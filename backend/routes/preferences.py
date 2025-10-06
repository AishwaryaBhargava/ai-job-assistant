# backend/routes/preferences.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from auth_utils import get_current_user
from database import profiles_collection
from models.preferences import PreferencePayload, PreferenceResponse
from utils.logger import logger  # ✅ Added logger

router = APIRouter()


# 📄 Fetch user preferences
@router.get("/", response_model=PreferenceResponse)
async def get_preferences(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    logger.info(f"Fetching preferences for user {user_id}")

    try:
        profile = await profiles_collection.find_one({"user_id": user_id}, {"preferences": 1, "_id": 0})
        if not profile or not profile.get("preferences"):
            logger.warning(f"No preferences found for user {user_id}")
            raise HTTPException(status_code=404, detail="Preferences not found")

        data = dict(profile["preferences"])
        updated_at = data.get("updated_at")
        if isinstance(updated_at, datetime):
            data["updated_at"] = updated_at

        logger.info(f"✅ Preferences retrieved successfully for user {user_id}")
        return PreferenceResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch preferences for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch preferences")


# 💾 Save or update user preferences
@router.post("/", response_model=PreferenceResponse)
async def save_preferences(payload: PreferencePayload, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    logger.info(f"Saving preferences for user {user_id}")

    try:
        stored = payload.dict()
        stored["updated_at"] = datetime.utcnow()

        update_result = await profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": {"preferences": stored}},
            upsert=True,
        )

        if update_result.modified_count or update_result.upserted_id:
            logger.debug(f"Preferences updated in DB for user {user_id}")
        else:
            logger.warning(f"No changes detected while saving preferences for user {user_id}")

        profile = await profiles_collection.find_one({"user_id": user_id}, {"preferences": 1, "_id": 0})
        if not profile or not profile.get("preferences"):
            logger.error(f"Failed to persist preferences for user {user_id}")
            raise HTTPException(status_code=500, detail="Failed to persist preferences")

        data = dict(profile["preferences"])
        logger.info(f"✅ Preferences saved successfully for user {user_id}")
        return PreferenceResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error saving preferences for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save preferences")
