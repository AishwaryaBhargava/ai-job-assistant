# backend/routes/saved_jobs.py
from fastapi import APIRouter, Depends, HTTPException
from database import saved_jobs_collection
from auth_utils import get_current_user
from utils.logger import logger  # ✅ Added logger

router = APIRouter()


# 💾 Save a job
@router.post("/save/{job_id}")
async def save_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Save a job for the logged-in user."""
    email = current_user["email"]
    logger.info(f"Attempting to save job '{job_id}' for user {email}")

    try:
        existing = await saved_jobs_collection.find_one({"email": email, "job_id": job_id})
        if existing:
            logger.warning(f"Job '{job_id}' already saved by {email}")
            raise HTTPException(status_code=400, detail="Job already saved")

        await saved_jobs_collection.insert_one({
            "email": email,
            "job_id": job_id,
        })
        logger.info(f"✅ Job '{job_id}' saved successfully for user {email}")
        return {"message": "Job saved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to save job '{job_id}' for user {email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save job")


# ❌ Unsave (remove) a saved job
@router.delete("/unsave/{job_id}")
async def unsave_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Remove a saved job."""
    email = current_user["email"]
    logger.info(f"Attempting to unsave job '{job_id}' for user {email}")

    try:
        result = await saved_jobs_collection.delete_one({"email": email, "job_id": job_id})
        if result.deleted_count == 0:
            logger.warning(f"Job '{job_id}' not found in saved list for user {email}")
            raise HTTPException(status_code=404, detail="Job not found")

        logger.info(f"✅ Job '{job_id}' removed from saved list for user {email}")
        return {"message": "Job removed from saved list"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to unsave job '{job_id}' for user {email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to remove job from saved list")


# 📄 List all saved jobs
@router.get("/my")
async def list_saved_jobs(current_user: dict = Depends(get_current_user)):
    """List all saved jobs for the logged-in user."""
    email = current_user["email"]
    logger.info(f"Fetching saved jobs for user {email}")

    try:
        jobs = await saved_jobs_collection.find({"email": email}).to_list(100)
        logger.info(f"✅ Retrieved {len(jobs)} saved jobs for user {email}")
        return {"count": len(jobs), "items": jobs}

    except Exception as e:
        logger.error(f"❌ Failed to fetch saved jobs for user {email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved jobs")
