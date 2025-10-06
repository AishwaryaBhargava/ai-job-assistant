from fastapi import APIRouter, Query, Body, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from services.ai_service import generate_answers_with_ai
from auth_utils import get_current_user
from utils.logger import logger  # ✅ Added logger

router = APIRouter()

# Request body model
class AnswerRequest(BaseModel):
    user_id: str
    profile_text: str   # summary of the user's profile (skills, experience)
    job_description: str

# Response body model
class AnswerResponse(BaseModel):
    id: str
    generated_answer: str


@router.post("/generate", response_model=AnswerResponse)
async def generate_answer(request: AnswerRequest = Body(...)):
    logger.info(f"Received AI answer generation request for user: {request.user_id}")
    try:
        logger.debug(f"Profile text length: {len(request.profile_text)}, JD length: {len(request.job_description)}")

        # Call AI service
        answer_text = generate_answers_with_ai(
            profile_text=request.profile_text,
            job_description=request.job_description
        )

        logger.info(f"✅ Successfully generated AI answer for user: {request.user_id}")
        return {
            "id": request.user_id,
            "generated_answer": answer_text
        }

    except Exception as e:
        logger.error(f"❌ Error generating AI answer for user {request.user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI answer generation failed. Please try again later.")
