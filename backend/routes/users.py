# backend/routes/users.py
from fastapi import APIRouter, HTTPException
from models.user import UserProfile
from database import users_collection
from bson import ObjectId
from utils.logger import logger  # ✅ Added logger

router = APIRouter()


# 📄 Get user profile
@router.get("/{user_id}")
async def get_user(user_id: str):
    logger.info(f"Fetching user profile for user_id={user_id}")

    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            logger.warning(f"User with id={user_id} not found")
            raise HTTPException(status_code=404, detail="User not found")

        user["_id"] = str(user["_id"])
        logger.info(f"✅ User profile retrieved successfully for user_id={user_id}")
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch user profile for id={user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch user profile")


# 📝 Update user profile
@router.put("/{user_id}")
async def update_user(user_id: str, profile: UserProfile):
    logger.info(f"Updating user profile for user_id={user_id}")

    try:
        update_result = await users_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": profile.dict()}
        )

        if update_result.modified_count == 0:
            logger.warning(f"User not found or not updated for user_id={user_id}")
            raise HTTPException(status_code=404, detail="User not found or not updated")

        logger.info(f"✅ User profile updated successfully for user_id={user_id}")
        return {"message": "User profile updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update user profile for id={user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update user profile")
