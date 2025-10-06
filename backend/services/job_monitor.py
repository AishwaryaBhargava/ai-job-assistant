import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId

from database import job_user_collection, jobs_collection
from utils.logger import logger

CHECK_INTERVAL_SECONDS = int(os.getenv("JOB_MONITOR_INTERVAL", str(24 * 60 * 60)))
STALE_AFTER_DAYS = int(os.getenv("JOB_STALE_AFTER_DAYS", "14"))

_monitor_task: Optional[asyncio.Task] = None


async def _record_status_change(job_id: str, status: str, reason: str) -> None:
    payload = {
        "status": status,
        "reason": reason,
        "timestamp": datetime.utcnow(),
    }
    await job_user_collection.update_many(
        {"job_id": job_id},
        {"$push": {"status_history": payload}},
    )
    logger.info(f"Recorded status change for job_id={job_id}, status={status}, reason={reason}")


async def _mark_job(job_id: str, status: str, reason: str) -> None:
    try:
        oid = ObjectId(job_id)
    except Exception:
        logger.warning(f"Invalid job id encountered while marking status: {job_id}")
        return

    await jobs_collection.update_one(
        {"_id": oid},
        {"$set": {"status": status, "last_status_change": datetime.utcnow()}},
    )
    await _record_status_change(job_id, status, reason)
    logger.info(f"Job {job_id} marked as {status} ({reason})")


async def run_monitor_cycle() -> None:
    now = datetime.utcnow()
    stale_threshold = now - timedelta(days=STALE_AFTER_DAYS)
    logger.info("Running job monitor cycle...")

    cursor = jobs_collection.find({"status": {"$ne": "closed"}}).limit(200)
    jobs = await cursor.to_list(length=200)
    logger.info(f"Fetched {len(jobs)} active jobs for monitoring check.")

    for job in jobs:
        job_id = str(job.get("_id"))
        metadata = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        source_status = str(metadata.get("source_status", ""))
        last_seen = job.get("last_seen_active")

        if source_status.lower() == "closed":
            await _mark_job(job_id, "closed", "source_reported_closed")
            continue

        if isinstance(last_seen, datetime) and last_seen < stale_threshold:
            await _mark_job(job_id, "stale", "stale_last_seen")
            continue

    logger.info("Job monitor cycle completed.")


async def _monitor_loop() -> None:
    while True:
        try:
            await run_monitor_cycle()
        except Exception as exc:
            logger.error(f"Job monitor cycle failed: {exc}", exc_info=True)
        logger.info(f"Sleeping for {CHECK_INTERVAL_SECONDS} seconds before next cycle...")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start_job_monitor() -> None:
    global _monitor_task
    if _monitor_task and not _monitor_task.done():
        logger.warning("Job monitor already running. Skipping restart.")
        return
    loop = asyncio.get_event_loop()
    _monitor_task = loop.create_task(_monitor_loop())
    logger.info("✅ Job monitor started.")


async def stop_job_monitor() -> None:
    global _monitor_task
    if not _monitor_task:
        logger.warning("No active job monitor to stop.")
        return

    _monitor_task.cancel()
    try:
        await _monitor_task
    except asyncio.CancelledError:
        logger.info("Job monitor stopped gracefully.")
    _monitor_task = None
