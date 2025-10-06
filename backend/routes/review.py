import io
import json
import os
import tempfile
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth_utils import get_current_user, get_optional_user
from database import fs, resume_reviews_collection
from models.review import ResumeReview, ResumeReviewResult
from services.ai_service import review_resume_with_ai
from services.parser_service import extract_text_from_file
from utils.logger import logger  # ✅ Added logger

router = APIRouter()


class ReviewRequest(BaseModel):
    resume_text: str


def _clean_document(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, list):
        return [_clean_document(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_document(item) for key, item in value.items()}
    return value


def _serialize_review(document: dict) -> dict:
    payload = document.copy()
    doc_id = payload.pop("_id", None)
    if doc_id is not None:
        payload["id"] = str(doc_id)

    created_at = payload.get("created_at")
    if isinstance(created_at, datetime):
        payload["created_at"] = created_at.isoformat()

    return _clean_document(payload)


def _public_review_payload(review: dict) -> dict:
    return {
        "ats_score": review.get("ats_score"),
        "summary_headline": review.get("summary_headline") or review.get("overall_feedback", ""),
    }


# 📄 Review resume text directly
@router.post("/review")
async def review_resume_text(
    payload: ReviewRequest,
    current_user: Optional[dict] = Depends(get_optional_user),
):
    logger.info("Received request for resume text review")
    try:
        review = await review_resume_with_ai(payload.resume_text)
        logger.info("✅ Resume text review completed successfully")

        if current_user:
            logger.info(f"User {current_user['_id']} performed a resume text review")
            return {
                "review_result": review,
                "resume_source": "text",
                "resume_text": payload.resume_text,
                "resume_filename": None,
            }
        logger.info("Returning public review payload (guest user)")
        return _public_review_payload(review)

    except ValueError as exc:
        logger.error(f"❌ AI service error during text review: {exc}")
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as e:
        logger.error(f"Unexpected error in review_resume_text: {e}", exc_info=True)
        raise


# 📎 Review uploaded resume file
@router.post("/review-file")
async def review_resume_file(
    file: UploadFile = File(...),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    logger.info(f"Received resume file for review: {file.filename}")
    filename = (file.filename or "").lower()

    if not filename:
        logger.warning("File review failed: missing filename")
        raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")

    allowed_suffixes = (".pdf", ".doc", ".docx", ".txt", ".rtf")
    if not any(filename.endswith(ext) for ext in allowed_suffixes):
        logger.warning(f"Unsupported file type attempted: {filename}")
        raise HTTPException(status_code=400, detail="Only PDF, DOC, DOCX, TXT, and RTF resumes are supported.")

    try:
        contents = await file.read()
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to read the uploaded resume.")

    if not contents:
        logger.warning("Uploaded file is empty")
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Determine file suffix
    suffix = next((ext for ext in allowed_suffixes if filename.endswith(ext)), ".pdf")

    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(contents)
            tmp_path = tmp_file.name
        logger.debug(f"Temporary file created: {tmp_path}")

        try:
            resume_text = extract_text_from_file(tmp_path) or ""
        except ValueError as exc:
            logger.error(f"Text extraction error: {exc}")
            raise HTTPException(status_code=400, detail=str(exc))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
            logger.debug(f"Temporary file deleted: {tmp_path}")

    if not resume_text.strip():
        logger.warning("Text extraction failed or resume is empty after parsing")
        raise HTTPException(
            status_code=400,
            detail="Could not extract text. Please upload a PDF, DOCX, TXT, or RTF file.",
        )

    try:
        review = await review_resume_with_ai(resume_text)
        logger.info(f"✅ Resume file review completed successfully: {file.filename}")
    except ValueError as exc:
        logger.error(f"AI error during resume file review: {exc}")
        raise HTTPException(status_code=502, detail=str(exc))

    if current_user:
        logger.info(f"User {current_user['_id']} reviewed a resume file: {file.filename}")
        return {
            "review_result": review,
            "resume_source": "file",
            "resume_filename": file.filename,
        }

    logger.info("Returning public review payload for guest user")
    return _public_review_payload(review)


# 💾 Save a reviewed resume
@router.post("/save")
async def save_resume_review(
    review_payload: str = Form(...),
    resume_source: str = Form(...),
    resume_text: Optional[str] = Form(None),
    resume_filename: Optional[str] = Form(None),
    file: UploadFile = File(None),
    current_user: dict = Depends(get_current_user),
):
    logger.info(f"Saving resume review for user: {current_user['_id']}")
    try:
        parsed = json.loads(review_payload)
        review_data = ResumeReviewResult.parse_obj(parsed).dict()
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in review payload", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid review payload.") from exc

    if resume_source not in {"text", "file"}:
        logger.warning(f"Invalid resume source: {resume_source}")
        raise HTTPException(status_code=400, detail="Unknown resume source.")

    resume_file_id: Optional[str] = None

    if resume_source == "text":
        if not resume_text or not resume_text.strip():
            logger.warning("Text source review missing resume text")
            raise HTTPException(status_code=400, detail="Resume text is required for manual entries.")
        resume_text = resume_text.strip()
    else:
        effective_filename = resume_filename or (file.filename if file else None)
        if not file or not effective_filename:
            logger.warning("File source review missing uploaded file")
            raise HTTPException(status_code=400, detail="Resume file is required for uploaded entries.")
        file_bytes = await file.read()
        if not file_bytes:
            logger.warning("Uploaded resume file is empty")
            raise HTTPException(status_code=400, detail="Uploaded resume is empty.")
        stream = io.BytesIO(file_bytes)
        grid_id = await fs.upload_from_stream(effective_filename, stream)
        resume_file_id = str(grid_id)
        resume_filename = effective_filename
        resume_text = None
        logger.info(f"Resume file stored in GridFS with ID: {resume_file_id}")

    record = ResumeReview(
        user_id=current_user["_id"],
        resume_text=resume_text,
        review_result=review_data,
        created_at=datetime.utcnow(),
        resume_source=resume_source,
        resume_filename=resume_filename if resume_source == "file" else None,
        resume_file_id=resume_file_id,
        ats_score_cache=review_data.get("ats_score"),
        quick_fix_titles=[
            fix.get("title")
            for fix in review_data.get("quick_fixes", [])
            if isinstance(fix, dict) and fix.get("title")
        ],
    )

    record_dict = record.dict(exclude_none=True)
    if resume_file_id:
        record_dict["resume_file_id"] = ObjectId(resume_file_id)

    inserted = await resume_reviews_collection.insert_one(record_dict)
    stored = await resume_reviews_collection.find_one({"_id": inserted.inserted_id})

    if not stored:
        logger.error("❌ Failed to save resume review in database")
        raise HTTPException(status_code=500, detail="Failed to save review.")

    logger.info(f"✅ Resume review saved successfully (ID: {inserted.inserted_id})")
    return {"item": _serialize_review(stored)}


# 📜 Get review history
@router.get("/history")
async def get_review_history(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    logger.info(f"Fetching resume review history for user: {current_user['_id']}")
    cursor = (
        resume_reviews_collection.find({"user_id": current_user["_id"]})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    items = []
    async for document in cursor:
        items.append(_serialize_review(document))

    logger.info(f"Returned {len(items)} resume reviews for user: {current_user['_id']}")
    return {"items": items}


# 📄 Get a single review history item
@router.get("/history/{review_id}")
async def get_review_history_item(review_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetching resume review record: {review_id}")
    try:
        oid = ObjectId(review_id)
    except (InvalidId, TypeError):
        logger.warning(f"Invalid review_id provided: {review_id}")
        raise HTTPException(status_code=404, detail="Review not found.")

    document = await resume_reviews_collection.find_one({"_id": oid, "user_id": current_user["_id"]})
    if not document:
        logger.warning(f"Review not found or unauthorized access: {review_id}")
        raise HTTPException(status_code=404, detail="Review not found.")

    logger.info(f"✅ Review record fetched successfully: {review_id}")
    return _serialize_review(document)


# ⬇️ Download the resume file from review history
@router.get("/history/{review_id}/download")
async def download_review_history_file(review_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"User {current_user['_id']} requested download for review file: {review_id}")
    try:
        oid = ObjectId(review_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Review not found.")

    document = await resume_reviews_collection.find_one({"_id": oid, "user_id": current_user["_id"]})
    if not document:
        raise HTTPException(status_code=404, detail="Review not found.")

    resume_file_id = document.get("resume_file_id")
    if not resume_file_id:
        raise HTTPException(status_code=404, detail="No resume file available for this review.")

    try:
        file_oid = resume_file_id if isinstance(resume_file_id, ObjectId) else ObjectId(resume_file_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Resume file not found.")

    stream = await fs.open_download_stream(file_oid)
    filename = document.get("resume_filename") or "resume"
    logger.info(f"Streaming resume file download: {filename}")

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(stream, media_type="application/octet-stream", headers=headers)


# ❌ Delete a resume review record
@router.delete("/history/{review_id}")
async def delete_review_history_item(review_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Deleting resume review record {review_id} for user {current_user['_id']}")
    try:
        oid = ObjectId(review_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Review not found.")

    document = await resume_reviews_collection.find_one({"_id": oid, "user_id": current_user["_id"]})
    if not document:
        logger.warning(f"Review not found for deletion: {review_id}")
        raise HTTPException(status_code=404, detail="Review not found.")

    resume_file_id = document.get("resume_file_id")
    if resume_file_id:
        try:
            file_oid = resume_file_id if isinstance(resume_file_id, ObjectId) else ObjectId(resume_file_id)
            await fs.delete(file_oid)
            logger.info(f"Deleted associated file for review {review_id}")
        except Exception as e:
            logger.error(f"Failed to delete file for review {review_id}: {e}")

    await resume_reviews_collection.delete_one({"_id": oid, "user_id": current_user["_id"]})
    logger.info(f"✅ Resume review record deleted successfully: {review_id}")

    return {"status": "deleted"}
