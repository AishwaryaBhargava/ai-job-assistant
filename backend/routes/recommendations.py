# backend/routes/recommendations.py
from fastapi import APIRouter, Depends, HTTPException, Query
from auth_utils import get_current_user
from models.preferences import GuestRecommendationRequest
from services import recommendation_service
from utils.logger import logger  # ✅ Added logger

router = APIRouter()


# 📄 Fetch AI-based job recommendations for logged-in user
@router.get("/")
async def list_recommendations(
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    logger.info(f"Fetching job recommendations for user {user_id} (limit={limit})")

    try:
        items = await recommendation_service.recommend_for_user(user_id, limit=limit)

        if not items:
            logger.warning(f"No recommendations found for user {user_id}")
            return {"items": [], "count": 0}

        logger.info(f"✅ {len(items)} recommendations fetched for user {user_id}")
        return {"items": items, "count": len(items)}

    except Exception as e:
        logger.error(f"❌ Failed to fetch recommendations for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch recommendations")


# 📄 Generate guest (unauthenticated) job recommendations
@router.post("/")
async def guest_recommendations(payload: GuestRecommendationRequest):
    logger.info("Generating guest job recommendations")

    try:
        items = await recommendation_service.recommend_for_guest(payload)

        if not items:
            logger.warning("No guest recommendations generated")
            return {"items": [], "count": 0}

        logger.info(f"✅ {len(items)} guest recommendations generated")
        return {"items": items, "count": len(items)}

    except Exception as e:
        logger.error(f"❌ Failed to generate guest recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate guest recommendations")
