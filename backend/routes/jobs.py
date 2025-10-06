# backend/routes/jobs.py
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from utils.logger import logger  # ✅ added logger

from services.scrapers import job_scraper
from models.job import RealtimeJobsResponse
from services.location_service import load_locations_from_csv, search_locations

router = APIRouter()


@router.get("/realtime", response_model=RealtimeJobsResponse)
async def get_realtime_jobs(
    what: Optional[str] = Query(None, description="Job title or keywords"),
    where: Optional[str] = Query(None, description="Location (e.g. 'San Francisco')"),
    max_days_old: Optional[int] = Query(None, description="Max job age in days"),
    salary_min: Optional[int] = Query(None, ge=0),
    salary_max: Optional[int] = Query(None, ge=0),
    full_time: Optional[bool] = Query(None, description="Full-time only"),
    contract: Optional[bool] = Query(None, description="Contract roles only"),
    remote_only: Optional[bool] = Query(None, description="Remote only"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=50, description="Results per page"),
    sort_by: Optional[str] = Query(
        None,
        description="Sort order: date | relevance | salary",
        regex="^(date|relevance|salary)$",
    ),
):
    """
    Fetch real-time jobs directly from Adzuna API.
    Always live → no DB storage.
    """
    logger.info(
        f"Fetching realtime jobs | what='{what}' | where='{where}' | remote={remote_only} | "
        f"salary_min={salary_min} | salary_max={salary_max} | page={page}"
    )

    try:
        jobs = job_scraper.fetch_realtime(
            what=what,
            where=where,
            max_days_old=max_days_old,
            salary_min=salary_min,
            salary_max=salary_max,
            full_time=full_time,
            contract=contract,
            remote_only=remote_only,
            page=page,
            results_per_page=page_size,
            sort_by=sort_by,
        )

        if not jobs:
            logger.warning(
                f"No realtime jobs found for query='{what}' in location='{where}'"
            )
            raise HTTPException(status_code=404, detail="No real-time jobs found")

        logger.info(
            f"✅ Found {len(jobs)} jobs for query='{what}' in location='{where}' (page {page})"
        )
        return {"items": jobs, "count": len(jobs), "page": page, "page_size": page_size}

    except ValueError as exc:
        logger.warning(f"Invalid job query parameters: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"❌ Job fetch failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Job fetch failed: {exc}") from exc


# 🔹 Preload CSV at startup
try:
    load_locations_from_csv()
    logger.info("✅ Locations CSV loaded successfully at startup")
except Exception as exc:
    logger.error(f"❌ Failed to preload locations CSV: {exc}", exc_info=True)


@router.get("/locations")
async def autocomplete_location(query: str):
    logger.info(f"Autocomplete location request for query='{query}'")
    try:
        suggestions = search_locations(query)
        logger.info(
            f"✅ Found {len(suggestions)} location suggestions for '{query}'"
        )
        return {"suggestions": suggestions}
    except Exception as exc:
        logger.error(f"❌ Location fetch failed for query='{query}': {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Location fetch failed: {exc}") from exc
