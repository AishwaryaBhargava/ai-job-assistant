# backend/routes/profile.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from models.user import UserProfile
from database import profiles_collection
from auth_utils import get_current_user
from utils.logger import logger  # ✅ Added logger
import os
import shutil
from urllib.parse import quote, unquote

router = APIRouter()

# Directory for storing resumes
UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# 📄 Get profile for logged-in user
@router.get("/")
async def get_profile(current_user: dict = Depends(get_current_user)):
    user_id = current_user["_id"]
    logger.info(f"Fetching profile for user {user_id}")

    try:
        profile = await profiles_collection.find_one({"user_id": user_id})
        if not profile:
            logger.warning(f"No profile found for user {user_id}")
            return {"message": "No profile found"}

        profile["_id"] = str(profile["_id"])

        # Handle resume URL and display name
        if profile.get("last_resume"):
            filename = os.path.basename(profile["last_resume"])
            encoded_name = quote(filename)
            profile["last_resume_url"] = f"/profile/resumes/{encoded_name}"
            raw_name = profile.get("last_resume_name") or (
                filename.split("_", 1)[1] if "_" in filename else filename
            )
            profile["last_resume_name"] = unquote(raw_name)

        logger.info(f"Profile retrieved successfully for user {user_id}")
        return profile
    except Exception as e:
        logger.error(f"❌ Error fetching profile for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch profile")


# 💾 Save or update profile
@router.post("/")
async def save_profile(profile: UserProfile, current_user: dict = Depends(get_current_user)):
    user_id = current_user["_id"]
    logger.info(f"Saving/updating profile for user {user_id}")

    try:
        profile_dict = profile.dict()
        profile_dict["user_id"] = user_id

        existing = await profiles_collection.find_one({"user_id": user_id})
        if existing:
            await profiles_collection.update_one(
                {"user_id": user_id}, {"$set": profile.dict()}
            )
            logger.info(f"Profile updated for user {user_id}")
            return {"message": "Profile updated"}
        else:
            await profiles_collection.insert_one(profile_dict)
            logger.info(f"Profile created for user {user_id}")
            return {"message": "Profile created"}
    except Exception as e:
        logger.error(f"❌ Failed to save/update profile for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save/update profile")


# 📤 Upload resume file & store path in profile
@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["_id"]
    logger.info(f"User {user_id} uploading resume: {file.filename}")

    try:
        original_filename = file.filename
        stored_filename = f"{user_id}_{original_filename}"
        file_path = os.path.join(UPLOAD_DIR, stored_filename)

        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.debug(f"Saved resume file at {file_path}")

        # Update profile with resume path and display name
        await profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": {"last_resume": file_path, "last_resume_name": original_filename}},
            upsert=True
        )

        logger.info(f"✅ Resume uploaded successfully for user {user_id}")
        return {
            "message": "Resume uploaded successfully",
            "file_path": file_path,
            "file_url": f"/profile/resumes/{quote(os.path.basename(file_path))}",
            "original_filename": original_filename
        }
    except Exception as e:
        logger.error(f"❌ Resume upload failed for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Resume upload failed: {str(e)}")


# 📥 Download resume for the current user
@router.get("/resumes/{encoded_filename:path}")
async def download_resume(encoded_filename: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["_id"]
    logger.info(f"User {user_id} requested resume download: {encoded_filename}")

    try:
        requested_name = unquote(encoded_filename)
        if not requested_name:
            raise HTTPException(status_code=404, detail="Resume not found")

        profile = await profiles_collection.find_one({"user_id": user_id})
        if not profile or not profile.get("last_resume"):
            raise HTTPException(status_code=404, detail="Resume not found")

        stored_filename = os.path.basename(profile["last_resume"])
        if stored_filename != requested_name:
            raise HTTPException(status_code=404, detail="Resume not found")

        file_path = os.path.abspath(profile["last_resume"])
        upload_root = os.path.abspath(UPLOAD_DIR)
        if os.path.commonpath([upload_root, file_path]) != upload_root:
            raise HTTPException(status_code=404, detail="Resume not found")

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Resume not found")

        download_name = profile.get("last_resume_name") or stored_filename
        download_name = unquote(download_name)
        logger.info(f"✅ Resume download successful for user {user_id}")
        return FileResponse(file_path, filename=download_name)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Resume download failed for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to download resume")


# 🗑️ Delete resume from profile and filesystem
@router.delete("/delete-resume")
async def delete_resume(current_user: dict = Depends(get_current_user)):
    user_id = current_user["_id"]
    logger.info(f"User {user_id} requested resume deletion")

    try:
        profile = await profiles_collection.find_one({"user_id": user_id})
        if not profile or "last_resume" not in profile or not profile["last_resume"]:
            logger.warning(f"No resume found for user {user_id}")
            raise HTTPException(status_code=404, detail="No resume found for this profile")

        file_path = profile["last_resume"]

        # Remove file from disk
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Deleted file from disk: {file_path}")

        # Remove DB references
        await profiles_collection.update_one(
            {"user_id": user_id},
            {"$unset": {"last_resume": "", "last_resume_name": ""}}
        )

        logger.info(f"✅ Resume deleted successfully for user {user_id}")
        return {"message": "Resume deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Resume delete failed for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Resume delete failed")
