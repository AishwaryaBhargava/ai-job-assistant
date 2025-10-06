from fastapi import APIRouter, Depends, HTTPException
from models.application import Application, Comment
from database import applications_collection
from bson import ObjectId
from auth_utils import get_current_user
from datetime import datetime
from utils.logger import logger  # ✅ Added logger

router = APIRouter()


# 📌 Add a new job application
@router.post("/", dependencies=[Depends(get_current_user)])
async def create_application(application: Application):
    logger.info("Received request to create new job application")
    try:
        app_dict = application.dict()

        # ✅ Convert HttpUrl → str
        if app_dict.get("url"):
            app_dict["url"] = str(app_dict["url"])

        # ✅ Ensure applied_on is stored properly
        if not app_dict.get("applied_on"):
            app_dict["applied_on"] = datetime.utcnow()

        # ✅ Normalize comment timestamps if present
        if "comments" in app_dict:
            for c in app_dict["comments"]:
                if isinstance(c.get("timestamp"), datetime):
                    c["timestamp"] = c["timestamp"].isoformat()

        result = await applications_collection.insert_one(app_dict)
        if result.inserted_id:
            logger.info(f"✅ Application created successfully with ID: {result.inserted_id}")
            return {"id": str(result.inserted_id), "message": "Application saved"}

        logger.error("❌ Failed to insert application — no ID returned")
        raise HTTPException(status_code=500, detail="Application not saved")

    except Exception as e:
        logger.error(f"Error while creating application: {e}", exc_info=True)
        raise


# 📌 Get all applications for a user
@router.get("/{user_id}", dependencies=[Depends(get_current_user)])
async def get_applications(user_id: str):
    logger.info(f"Fetching applications for user: {user_id}")
    try:
        applications = []
        async for app in applications_collection.find({"user_id": user_id}):
            app["_id"] = str(app["_id"])
            applications.append(app)

        logger.info(f"Found {len(applications)} applications for user {user_id}")
        return applications

    except Exception as e:
        logger.error(f"Error fetching applications for user {user_id}: {e}", exc_info=True)
        raise


# 📌 Update application fields (status, next_action, etc.)
@router.patch("/{app_id}", dependencies=[Depends(get_current_user)])
async def update_application(app_id: str, updates: dict):
    logger.info(f"Updating application {app_id} with fields: {list(updates.keys())}")
    try:
        updates["last_updated"] = datetime.utcnow()  # ✅ auto-track updates

        if "url" in updates and updates["url"]:
            updates["url"] = str(updates["url"])

        result = await applications_collection.update_one(
            {"_id": ObjectId(app_id)},
            {"$set": updates}
        )

        if result.modified_count == 0:
            logger.warning(f"No changes made or application not found: {app_id}")
            raise HTTPException(status_code=404, detail="Application not found or no changes made")

        logger.info(f"✅ Application updated successfully: {app_id}")
        return {"message": "Application updated"}

    except Exception as e:
        logger.error(f"Error updating application {app_id}: {e}", exc_info=True)
        raise


# 📌 Add a comment to an application
@router.post("/{app_id}/comments", dependencies=[Depends(get_current_user)])
async def add_comment(app_id: str, comment: Comment):
    logger.info(f"Adding comment to application: {app_id}")
    try:
        new_comment = comment.dict()
        new_comment["timestamp"] = datetime.utcnow()  # always overwrite with now()

        result = await applications_collection.update_one(
            {"_id": ObjectId(app_id)},
            {"$push": {"comments": new_comment}}
        )

        if result.modified_count == 0:
            logger.warning(f"Application not found while adding comment: {app_id}")
            raise HTTPException(status_code=404, detail="Application not found")

        logger.info(f"✅ Comment added successfully to application: {app_id}")
        return {"message": "Comment added"}

    except Exception as e:
        logger.error(f"Error adding comment to application {app_id}: {e}", exc_info=True)
        raise


# 📌 Save a job (store in applications DB with status="saved")
@router.post("/save", dependencies=[Depends(get_current_user)])
async def save_job(request: dict, user=Depends(get_current_user)):
    logger.info(f"User {user['_id']} attempting to save job: {request.get('job_title')}")
    try:
        job_id = request.get("job_id")
        job_title = request.get("job_title")
        company = request.get("company")
        url = request.get("url")
        location = request.get("location")

        if not job_id or not job_title:
            logger.warning("Job ID or title missing in save request")
            raise HTTPException(status_code=400, detail="Job ID and title required")

        existing = await applications_collection.find_one({
            "user_id": user["_id"],
            "job_id": job_id
        })

        if existing:
            logger.warning(f"Job already saved by user {user['_id']}: {job_id}")
            raise HTTPException(status_code=400, detail="Job already saved")

        new_application = {
            "user_id": user["_id"],
            "job_id": job_id,
            "job_title": job_title,
            "company": company or "Unknown company",
            "location": location or "",
            "url": str(url) if url else "",
            "status": "saved",           # ✅ aligns with dashboard filters
            "applied_on": None,
            "last_updated": datetime.utcnow(),
            "next_action": None,
            "comments": []
        }

        result = await applications_collection.insert_one(new_application)
        logger.info(f"✅ Job saved successfully (job_id={job_id}, user={user['_id']})")
        return {"message": "Job saved", "id": str(result.inserted_id)}

    except Exception as e:
        logger.error(f"Error while saving job for user {user['_id']}: {e}", exc_info=True)
        raise


# 📌 Unsave a job (delete saved status entry)
@router.delete("/unsave/{job_id}", dependencies=[Depends(get_current_user)])
async def unsave_job(job_id: str, user=Depends(get_current_user)):
    logger.info(f"User {user['_id']} attempting to unsave job {job_id}")
    try:
        result = await applications_collection.delete_one({
            "user_id": user["_id"],
            "job_id": job_id,
            "status": "saved"
        })

        if result.deleted_count == 0:
            logger.warning(f"Saved job not found for user {user['_id']}: {job_id}")
            raise HTTPException(status_code=404, detail="Saved job not found")

        logger.info(f"✅ Job unsaved successfully (user={user['_id']}, job={job_id})")
        return {"message": "Job unsaved"}

    except Exception as e:
        logger.error(f"Error unsaving job {job_id} for user {user['_id']}: {e}", exc_info=True)
        raise


# 📌 Delete an application (any type — saved, submitted, etc.)
@router.delete("/{app_id}", dependencies=[Depends(get_current_user)])
async def delete_application(app_id: str, user=Depends(get_current_user)):
    logger.info(f"User {user['_id']} attempting to delete application {app_id}")
    try:
        result = await applications_collection.delete_one({
            "_id": ObjectId(app_id),
            "user_id": user["_id"]
        })

        if result.deleted_count == 0:
            logger.warning(f"Application not found or unauthorized: {app_id}")
            raise HTTPException(status_code=404, detail="Application not found or unauthorized")

        logger.info(f"✅ Application deleted successfully: {app_id}")
        return {"message": "Application deleted"}

    except Exception as e:
        logger.error(f"Error deleting application {app_id}: {e}", exc_info=True)
        raise
