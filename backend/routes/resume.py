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
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from auth_utils import get_current_user
from database import fs, resumes_collection
from models.resume import Resume, ResumeAnalysis
from services.ai_service import analyze_resume_with_ai
from services.parser_service import extract_text_from_file
from typing import Optional
from utils.logger import logger  # ✅ Added logger

router = APIRouter()

def _clean_document(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, list):
        return [_clean_document(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_document(item) for key, item in value.items()}
    return value


def _serialize_analysis(document: dict) -> dict:
    document = document.copy()
    document_id = document.pop("_id", None)
    if document_id is not None:
        document["id"] = str(document_id)

    created_at = document.get("created_at")
    if isinstance(created_at, datetime):
        document["created_at"] = created_at.isoformat()

    return _clean_document(document)


@router.post("/analyze")
async def analyze_resume(
    job_description: str = Query(..., description="Job description to compare against"),
    resume: Resume = Body(...),
):
    logger.info("Analyzing resume from text input")
    
    try:
        logger.info(f"Calling AI service to analyze resume (job_description length: {len(job_description)} chars)")
        analysis = await analyze_resume_with_ai(resume.resume_text, job_description)

        if not isinstance(analysis, dict):
            logger.error("❌ AI service did not return a valid dict")
            raise HTTPException(status_code=500, detail="AI did not return a valid dict")

        logger.info("✅ Resume analysis completed successfully")
        return {
            "analysis_result": analysis,
            "resume_source": "text",
            "resume_text": resume.resume_text,
            "job_description": job_description,
            "resume_filename": None,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to analyze resume: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze resume")


@router.post("/analyze-file")
async def analyze_resume_file(
    job_description: str = Form(..., description="Job description to compare against"),
    file: UploadFile = File(...),
):
    logger.info(f"Analyzing resume from uploaded file: {file.filename}")
    
    try:
        filename = (file.filename or "").lower()
        if not filename:
            logger.warning("Uploaded file has no valid filename")
            raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")

        allowed_suffixes = (".pdf", ".doc", ".docx", ".txt", ".rtf")
        if not any(filename.endswith(ext) for ext in allowed_suffixes):
            logger.warning(f"Unsupported file type: {filename}")
            raise HTTPException(status_code=400, detail="Only PDF, DOC, DOCX, TXT, and RTF resumes are supported.")

        try:
            logger.info(f"Reading uploaded file: {filename}")
            contents = await file.read()
        except Exception as e:
            logger.error(f"❌ Failed to read uploaded file: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail="Failed to read the uploaded resume.")

        if not contents:
            logger.warning(f"Uploaded file is empty: {filename}")
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        if filename.endswith(".pdf"):
            suffix = ".pdf"
        elif filename.endswith(".docx"):
            suffix = ".docx"
        elif filename.endswith(".doc"):
            suffix = ".doc"
        elif filename.endswith(".txt"):
            suffix = ".txt"
        else:
            suffix = ".rtf"

        tmp_path: Optional[str] = None

        try:
            logger.info(f"Creating temporary file with suffix: {suffix}")
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(contents)
                tmp_path = tmp_file.name
            logger.info(f"Temporary file created at: {tmp_path}")

            try:
                logger.info(f"Extracting text from file: {filename}")
                resume_text = extract_text_from_file(tmp_path) or ""
                logger.info(f"✅ Text extracted successfully (length: {len(resume_text)} chars)")
            except ValueError as exc:
                logger.error(f"❌ Text extraction failed with ValueError: {exc}", exc_info=True)
                raise HTTPException(status_code=400, detail=str(exc))
        finally:
            if tmp_path and os.path.exists(tmp_path):
                logger.info(f"Cleaning up temporary file: {tmp_path}")
                os.unlink(tmp_path)

        if not resume_text.strip():
            logger.warning(f"No text could be extracted from file: {filename}")
            raise HTTPException(
                status_code=400,
                detail="Could not extract text. Please upload a PDF, DOCX, TXT, or RTF file.",
            )

        logger.info(f"Calling AI service to analyze resume from file (job_description length: {len(job_description)} chars)")
        analysis = await analyze_resume_with_ai(resume_text, job_description)

        if not isinstance(analysis, dict):
            logger.error("❌ AI service did not return a valid dict")
            raise HTTPException(status_code=500, detail="AI did not return a valid dict")

        logger.info(f"✅ Resume file analysis completed successfully for file: {filename}")
        return {
            "analysis_result": analysis,
            "resume_source": "file",
            "resume_text": None,
            "job_description": job_description,
            "resume_filename": file.filename,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to analyze resume file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze resume file")


@router.post("/history")
async def save_resume_history(
    resume_source: str = Form(...),
    job_description: str = Form(...),
    analysis_result: str = Form(...),
    resume_text: Optional[str] = Form(None),
    resume_filename: Optional[str] = Form(None),
    file: UploadFile = File(None),
    current_user: dict = Depends(get_current_user),
):
    logger.info(f"Saving resume history for user_id={current_user['_id']}, resume_source={resume_source}")
    
    try:
        try:
            analysis_payload = json.loads(analysis_result)
            logger.info("Analysis result parsed successfully")
        except json.JSONDecodeError as exc:
            logger.error(f"❌ Invalid analysis payload JSON: {exc}", exc_info=True)
            raise HTTPException(status_code=400, detail="Invalid analysis payload.") from exc

        if resume_source not in {"text", "file"}:
            logger.warning(f"Unknown resume source: {resume_source}")
            raise HTTPException(status_code=400, detail="Unknown resume source.")

        if resume_source == "text":
            if not resume_text or not resume_text.strip():
                logger.warning("Resume text is missing for text-based entry")
                raise HTTPException(status_code=400, detail="Resume text is required for manual entries.")
            resume_file_id = None
            logger.info("Processing text-based resume entry")
        else:
            if not file or not resume_filename:
                logger.warning("Resume file is missing for file-based entry")
                raise HTTPException(status_code=400, detail="Resume file is required for uploaded entries.")
            
            logger.info(f"Reading uploaded file: {resume_filename}")
            file_bytes = await file.read()
            if not file_bytes:
                logger.warning(f"Uploaded resume file is empty: {resume_filename}")
                raise HTTPException(status_code=400, detail="Uploaded resume is empty.")
            
            logger.info(f"Uploading file to GridFS: {resume_filename}")
            stream = io.BytesIO(file_bytes)
            grid_id = await fs.upload_from_stream(resume_filename, stream)
            resume_file_id = str(grid_id)
            logger.info(f"✅ File uploaded to GridFS with id={resume_file_id}")

        record = ResumeAnalysis(
            user_id=current_user["_id"],
            resume_text=resume_text.strip() if resume_source == "text" else None,
            job_description=job_description,
            analysis_result=analysis_payload,
            created_at=datetime.utcnow(),
            resume_source=resume_source,
            resume_filename=resume_filename if resume_source == "file" else None,
            resume_file_id=resume_file_id,
        )

        record_dict = record.dict(exclude_none=True)
        if resume_file_id:
            record_dict["resume_file_id"] = ObjectId(resume_file_id)

        logger.info(f"Inserting resume analysis record into database for user_id={current_user['_id']}")
        inserted = await resumes_collection.insert_one(record_dict)
        stored = await resumes_collection.find_one({"_id": inserted.inserted_id})

        if not stored:
            logger.error(f"❌ Failed to retrieve saved analysis with id={inserted.inserted_id}")
            raise HTTPException(status_code=500, detail="Failed to save analysis.")

        logger.info(f"✅ Resume history saved successfully with id={inserted.inserted_id}")
        return {"item": _serialize_analysis(stored)}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to save resume history for user_id={current_user['_id']}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save resume history")


@router.get("/history")
async def get_resume_history(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    logger.info(f"Fetching resume history for user_id={current_user['_id']}, limit={limit}, skip={skip}")
    
    try:
        cursor = (
            resumes_collection.find({"user_id": current_user["_id"]})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        items = []
        async for document in cursor:
            items.append(_serialize_analysis(document))

        logger.info(f"✅ Retrieved {len(items)} resume history items for user_id={current_user['_id']}")
        return {"items": items}
    
    except Exception as e:
        logger.error(f"❌ Failed to fetch resume history for user_id={current_user['_id']}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch resume history")


@router.get("/history/{analysis_id}")
async def get_resume_history_item(analysis_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Fetching resume history item for analysis_id={analysis_id}, user_id={current_user['_id']}")
    
    try:
        try:
            oid = ObjectId(analysis_id)
        except (InvalidId, TypeError) as e:
            logger.warning(f"Invalid analysis_id format: {analysis_id}")
            raise HTTPException(status_code=404, detail="Analysis not found.")

        document = await resumes_collection.find_one({"_id": oid, "user_id": current_user["_id"]})
        if not document:
            logger.warning(f"Analysis not found for analysis_id={analysis_id}, user_id={current_user['_id']}")
            raise HTTPException(status_code=404, detail="Analysis not found.")

        logger.info(f"✅ Resume history item retrieved successfully for analysis_id={analysis_id}")
        return _serialize_analysis(document)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch resume history item for analysis_id={analysis_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch resume history item")


@router.get("/history/{analysis_id}/download")
async def download_resume_history_file(analysis_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Downloading resume file for analysis_id={analysis_id}, user_id={current_user['_id']}")
    
    try:
        try:
            oid = ObjectId(analysis_id)
        except (InvalidId, TypeError):
            logger.warning(f"Invalid analysis_id format: {analysis_id}")
            raise HTTPException(status_code=404, detail="Analysis not found.")

        document = await resumes_collection.find_one({"_id": oid, "user_id": current_user["_id"]})
        if not document:
            logger.warning(f"Analysis not found for analysis_id={analysis_id}, user_id={current_user['_id']}")
            raise HTTPException(status_code=404, detail="Analysis not found.")

        resume_file_id = document.get("resume_file_id")
        if not resume_file_id:
            logger.warning(f"No resume file available for analysis_id={analysis_id}")
            raise HTTPException(status_code=404, detail="No resume file available for this analysis.")

        try:
            file_oid = resume_file_id if isinstance(resume_file_id, ObjectId) else ObjectId(resume_file_id)
        except (InvalidId, TypeError):
            logger.error(f"❌ Invalid resume_file_id format: {resume_file_id}")
            raise HTTPException(status_code=404, detail="Resume file not found.")

        logger.info(f"Opening download stream for file_id={file_oid}")
        stream = await fs.open_download_stream(file_oid)
        filename = document.get("resume_filename") or "resume"

        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        logger.info(f"✅ Resume file download initiated for analysis_id={analysis_id}, filename={filename}")
        return StreamingResponse(stream, media_type="application/octet-stream", headers=headers)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download resume file for analysis_id={analysis_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to download resume file")


@router.delete("/history/{analysis_id}")
async def delete_resume_history_item(analysis_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"Deleting resume history item for analysis_id={analysis_id}, user_id={current_user['_id']}")
    
    try:
        try:
            oid = ObjectId(analysis_id)
        except (InvalidId, TypeError):
            logger.warning(f"Invalid analysis_id format: {analysis_id}")
            raise HTTPException(status_code=404, detail="Analysis not found.")

        document = await resumes_collection.find_one({"_id": oid, "user_id": current_user["_id"]})
        if not document:
            logger.warning(f"Analysis not found for analysis_id={analysis_id}, user_id={current_user['_id']}")
            raise HTTPException(status_code=404, detail="Analysis not found.")

        resume_file_id = document.get("resume_file_id")
        if resume_file_id:
            try:
                file_oid = resume_file_id if isinstance(resume_file_id, ObjectId) else ObjectId(resume_file_id)
                logger.info(f"Deleting associated file from GridFS: file_id={file_oid}")
                await fs.delete(file_oid)
                logger.info(f"✅ Associated file deleted from GridFS: file_id={file_oid}")
            except Exception as e:
                # Ignore deletion failures for the file but continue removing the record
                logger.warning(f"Failed to delete file from GridFS (file_id={file_oid}), continuing with record deletion: {e}")
                pass

        logger.info(f"Deleting resume analysis record from database: analysis_id={analysis_id}")
        await resumes_collection.delete_one({"_id": oid, "user_id": current_user["_id"]})

        logger.info(f"✅ Resume history item deleted successfully for analysis_id={analysis_id}")
        return {"status": "deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete resume history item for analysis_id={analysis_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete resume history item")

def _pick_numeric_score(analysis: dict) -> Optional[float]:
    """
    Try to find a numeric score inside the analysis dict. Accepts common keys and
    normalizes to 0..100 (if 0..1, multiply by 100; if '82%', strip and parse).
    """
    if not isinstance(analysis, dict):
        return None

    candidate_keys = [
        "score", "match_score", "ats_score", "resume_match_score",
        "overall_score", "overall", "match"
    ]

    val = None
    for k in candidate_keys:
        if k in analysis:
            val = analysis[k]
            break
    if val is None:
        # Sometimes it's nested (e.g., {"scores":{"overall": 0.83}})
        scores = analysis.get("scores")
        if isinstance(scores, dict):
            for k in candidate_keys:
                if k in scores:
                    val = scores[k]
                    break

    if val is None:
        return None

    # Normalize common formats
    if isinstance(val, str):
        s = val.strip().replace("%", "")
        try:
            num = float(s)
            # assume already 0..100
            return max(0.0, min(100.0, num))
        except ValueError:
            return None

    if isinstance(val, (int, float)):
        # If it looks like 0..1, convert to %
        if 0.0 <= float(val) <= 1.0:
            return round(float(val) * 100.0, 2)
        return round(float(val), 2)

    return None


@router.post("/score", dependencies=[Depends(get_current_user)])
async def get_resume_score_for_current_user(
    payload: dict = Body(..., description="{'job_description': '...'}"),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns a single numeric score (0..100) for how well the user's latest resume
    matches the provided job description.
    """
    logger.info(f"Getting resume score for user_id={current_user['_id']}")
    
    try:
        job_description = (payload or {}).get("job_description", "")
        if not isinstance(job_description, str) or len(job_description.strip()) < 20:
            logger.warning(f"Invalid job_description (length: {len(job_description) if isinstance(job_description, str) else 'N/A'})")
            raise HTTPException(status_code=400, detail="job_description is required and should be meaningful.")

        # 1) Find the user's most recent resume record in history.
        logger.info(f"Finding most recent resume for user_id={current_user['_id']}")
        doc = await resumes_collection.find_one(
            {"user_id": current_user["_id"]},
            sort=[("created_at", -1)]
        )
        if not doc:
            logger.warning(f"No resume found for user_id={current_user['_id']}")
            raise HTTPException(status_code=404, detail="No resume found for the user.")

        logger.info(f"Found resume record with id={doc['_id']}")

        # 2) Get resume text: prefer stored text; if file only, extract quickly.
        resume_text: Optional[str] = doc.get("resume_text")
        if not resume_text:
            logger.info("No resume_text found in record, attempting to extract from file")
            resume_file_id = doc.get("resume_file_id")
            if not resume_file_id:
                logger.warning("No resume text or file available in record")
                raise HTTPException(status_code=404, detail="No resume text/file found.")
            # Download from GridFS and extract text
            try:
                file_oid = resume_file_id if isinstance(resume_file_id, ObjectId) else ObjectId(resume_file_id)
                logger.info(f"Downloading resume file from GridFS: file_id={file_oid}")
                stream = await fs.open_download_stream(file_oid)
                contents = await stream.read()
                logger.info(f"✅ Resume file downloaded successfully (size: {len(contents)} bytes)")
            except Exception as e:
                logger.error(f"❌ Failed to load resume file from GridFS: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Failed to load resume file.")
            # Write to tmp file and parse via existing parser
            suffix = ".pdf"  # best default; parser handles multiple types
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmpf:
                tmpf.write(contents)
                tmp_path = tmpf.name
            logger.info(f"Created temporary file for text extraction: {tmp_path}")
            try:
                resume_text = extract_text_from_file(tmp_path) or ""
                logger.info(f"✅ Text extracted from file (length: {len(resume_text)} chars)")
            finally:
                try:
                    os.unlink(tmp_path)
                    logger.info(f"Cleaned up temporary file: {tmp_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {tmp_path}: {e}")
                    pass

        if not resume_text or not resume_text.strip():
            logger.warning("Could not obtain usable resume text")
            raise HTTPException(status_code=400, detail="Could not obtain usable resume text.")

        # 3) Call your existing analyzer (already used by /resume/analyze)
        logger.info(f"Analyzing resume for score calculation (resume length: {len(resume_text)} chars, job_description length: {len(job_description)} chars)")
        analysis = await analyze_resume_with_ai(resume_text, job_description)
        if not isinstance(analysis, dict):
            logger.error("❌ AI service did not return a valid dict")
            raise HTTPException(status_code=500, detail="AI did not return a valid dict")

        # 4) Extract a numeric score and return it
        logger.info("Extracting numeric score from analysis result")
        score = _pick_numeric_score(analysis)
        if score is None:
            # Fall back to 0; still return success but with score=0
            logger.warning("Could not extract numeric score from analysis, defaulting to 0.0")
            score = 0.0
        else:
            logger.info(f"✅ Extracted score: {score}")

        logger.info(f"✅ Resume score calculated successfully for user_id={current_user['_id']}, score={score}")
        return {"score": round(score, 2)}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to calculate resume score for user_id={current_user['_id']}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate resume score")