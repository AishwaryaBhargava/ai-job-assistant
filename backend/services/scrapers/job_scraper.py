import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from utils.logger import logger

JobPayload = Dict[str, Any]

# Adzuna API credentials
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
    logger.error("Adzuna API credentials not set (ADZUNA_APP_ID, ADZUNA_APP_KEY).")
    raise RuntimeError("Missing Adzuna API credentials. Please set env vars ADZUNA_APP_ID and ADZUNA_APP_KEY.")

# Base API URL (US jobs for now)
BASE_URL = "https://api.adzuna.com/v1/api/jobs/us/search/{page}"


def fetch_realtime(
    what: Optional[str] = None,
    where: Optional[str] = None,
    max_days_old: Optional[int] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    full_time: Optional[bool] = None,
    contract: Optional[bool] = None,
    remote_only: Optional[bool] = None,
    page: int = 1,
    results_per_page: int = 20,
    sort_by: Optional[str] = None,
) -> List[JobPayload]:
    """
    Fetch real-time job listings directly from Adzuna API.
    Returns normalized job payloads.
    """
    logger.info(f"Fetching realtime jobs from Adzuna API (page={page}, results_per_page={results_per_page})")
    
    try:
        params: Dict[str, Any] = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "results_per_page": results_per_page,
            "content-type": "application/json",
        }

        if what:
            params["what"] = what
        if where:
            params["where"] = where
        if max_days_old:
            params["max_days_old"] = max_days_old
        if salary_min:
            params["salary_min"] = salary_min
        if salary_max:
            params["salary_max"] = salary_max
        if full_time:
            params["full_time"] = 1
        if contract:
            params["contract"] = 1
        if remote_only:
            params["what_and"] = "remote"
        if sort_by in {"date", "relevance", "salary"}:
            params["sort_by"] = sort_by

        logger.info(f"Adzuna API filters: what={what}, where={where}, max_days_old={max_days_old}, remote_only={remote_only}, sort_by={sort_by}")

        url = BASE_URL.format(page=page)

        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        jobs: List[JobPayload] = []
        results = data.get("results", [])
        
        for job in results:
            jobs.append(_normalize_job(job))

        logger.info(f"✅ Fetched and normalized {len(jobs)} jobs from Adzuna (page={page})")
        return jobs
    
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error fetching from Adzuna API: {e.response.status_code}", exc_info=True)
        raise
    except httpx.TimeoutException as e:
        logger.error(f"❌ Timeout fetching from Adzuna API: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch realtime jobs from Adzuna: {e}", exc_info=True)
        raise


def _normalize_job(job: Dict[str, Any]) -> JobPayload:
    """Convert Adzuna job response into our unified job format."""
    job_id = job.get("id")
    logger.info(f"Normalizing Adzuna job with id={job_id}")
    
    try:
        now = datetime.utcnow()
        location_data = job.get("location", {})
        area = location_data.get("area", [])

        # Extract country (first element) and city (last element)
        country = area[0] if len(area) > 0 else None
        city = area[-1] if len(area) > 0 else None

        # Build display location: prefer "City, Country", fallback to Adzuna's display_name
        if city and country:
            display_location = f"{city}, {country}"
        elif location_data.get("display_name"):
            display_location = location_data.get("display_name")
        else:
            display_location = None

        result = {
            "source": "adzuna",
            "source_id": str(job_id),
            "title": job.get("title"),
            "company": job.get("company", {}).get("display_name"),
            "city": city,
            "country": country,
            "locations": [display_location] if display_location else [],
            "work_modes": ["remote"] if job.get("remote") else ["onsite"],
            "categories": [job.get("category", {}).get("label")] if job.get("category") else [],
            "levels": [],
            "skills": [],
            "description": job.get("description"),
            "salary": {
                "currency": job.get("salary_currency"),
                "min": job.get("salary_min"),
                "max": job.get("salary_max"),
                "predicted": job.get("salary_is_predicted"),
            },
            "url": job.get("redirect_url"),
            "metadata": {
                "industry": [job.get("category", {}).get("label")] if job.get("category") else [],
                "collected_at": now.isoformat(),
            },
            "last_seen_active": now,
            "collected_at": now,
        }
        
        logger.info(f"✅ Normalized Adzuna job: id={job_id}, title={result['title']}, company={result['company']}")
        return result
    
    except Exception as e:
        logger.error(f"❌ Failed to normalize Adzuna job with id={job_id}: {e}", exc_info=True)
        raise


def fetch_location_suggestions(query: str) -> List[str]:
    logger.info(f"Fetching location suggestions for query='{query}'")
    
    try:
        if not query:
            logger.info("Empty query provided, returning empty list")
            return []

        url = f"https://api.teleport.org/api/cities/?search={query}"

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

            suggestions = []
            for item in data.get("_embedded", {}).get("city:search-results", []):
                match = item.get("matching_full_name")
                if match:
                    suggestions.append(match)

            result = suggestions[:10]  # limit results
            logger.info(f"✅ Fetched {len(result)} location suggestions from Teleport API")
            return result

        except Exception as exc:
            # Log error but return fallback list instead of failing
            logger.warning(f"Teleport API request failed: {exc}, using fallback cities")
            fallback_cities = [
                "New York, United States",
                "San Francisco, United States",
                "Los Angeles, United States",
                "Seattle, United States",
                "Chicago, United States",
                "Boston, United States",
                "Washington, United States",
            ]
            filtered = [c for c in fallback_cities if query.lower() in c.lower()]
            logger.info(f"Returning {len(filtered)} fallback cities matching query")
            return filtered
    
    except Exception as e:
        logger.error(f"❌ Failed to fetch location suggestions for query='{query}': {e}", exc_info=True)
        raise