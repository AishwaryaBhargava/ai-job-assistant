# routes/feedback.py
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from utils.logger import logger

router = APIRouter()

class FeedbackItem(BaseModel):
    item_text: str
    feedback_type: str  # "up" or "down"
    source: str         # "resume_reviewer" or "resume_analyzer"
    user_id: str | None = None


@router.post("/", summary="Receive AI feedback")
async def receive_feedback(payload: FeedbackItem, request: Request):
    logger.info(f"📩 Feedback received: {payload.dict()}")
    # TODO: Store to database (optional)
    return {"status": "ok", "message": "Feedback recorded"}
