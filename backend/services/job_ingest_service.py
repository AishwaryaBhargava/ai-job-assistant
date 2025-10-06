import inspect
import time
from typing import Dict, Iterable, List, Any

from utils.logger import logger
from services import recommendation_service
from services.scrapers import job_scraper

SCRAPERS: Dict[str, callable] = {
    "adzuna": job_scraper.fetch_latest,
}

def available_sources() -> List[str]:
    logger.info("Listing available job scraper sources.")
    return sorted(SCRAPERS.keys())

async def run_scraper(source: str, filters: Dict[str, Any] = None) -> List[str]:
    start_time = time.time()
    """
    Run a scraper for a given source with optional filters.
    Example filters: {"what": "software engineer", "where": "new york", "max_days_old": 7}
    """
    logger.info(f"Running scraper for source='{source}' with filters={filters or {}}")

    fetcher = SCRAPERS.get(source)
    if not fetcher:
        raise ValueError(f"Unknown scraper source '{source}'. Available: {', '.join(available_sources())}")

    filters = filters or {}
    result = fetcher(**filters)
    jobs = await result if inspect.isawaitable(result) else result

    if not isinstance(jobs, Iterable):
        raise ValueError(f"Scraper '{source}' returned an invalid payload")

    inserted_ids: List[str] = []
    total, success = 0, 0

    for job in jobs:
        total += 1
        payload = dict(job or {})
        description = payload.get("description")
        if not description:
            continue
        payload.setdefault("source", source)
        payload.setdefault("metadata", {})
        payload.setdefault("last_seen_active", payload.get("collected_at"))
        try:
            job_id = await recommendation_service.upsert_job(payload)
            inserted_ids.append(job_id)
            success += 1
        except Exception as e:
            logger.error(f"Failed to insert job from '{source}': {e}")

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"Scraper '{source}' completed — {success}/{total} jobs processed in {elapsed}s")
    return inserted_ids

async def run_multiple(sources: Iterable[str], filters: Dict[str, Any] = None) -> Dict[str, List[str]]:
    """
    Run multiple scrapers in one go.
    """
    logger.info(f"Running multiple scrapers: {', '.join(sources)}")
    start_time = time.time()
    summary: Dict[str, List[str]] = {}

    for source in sources:
        try:
            summary[source] = await run_scraper(source, filters)
        except Exception as e:
            logger.error(f"Error running scraper '{source}': {e}")
            summary[source] = []

    logger.info(f"All scrapers completed in {round(time.time() - start_time, 2)}s")
    return summary
