# backend/routes/resume_upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
import tempfile
import io
from services.parser_service import extract_text_from_file, parse_resume_text
from database import fs, resumes_collection
from auth_utils import get_current_user
from bson import ObjectId
from utils.logger import logger  # ✅ Added logger

router = APIRouter()


# 📤 Upload a resume
@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a resume (.pdf or .docx), save it in GridFS, extract + parse text,
    and return AI-parsed structured info.
    """
    logger.info(f"User {current_user['_id']} uploading resume: {file.filename}")
    try:
        # ✅ Ensure supported file type
        if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx")):
            logger.warning(f"Unsupported file type attempted: {file.filename}")
            raise HTTPException(status_code=400, detail="Only .pdf and .docx files are supported")

        # ✅ Save to a temporary file
        suffix = ".pdf" if file.filename.endswith(".pdf") else ".docx"
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        logger.debug(f"Temporary file created at {tmp_path}")

        # ✅ Extract raw text
        raw_text = extract_text_from_file(tmp_path)
        logger.info(f"Extracted {len(raw_text)} characters from resume {file.filename}")

        # ✅ AI parsing (with fallback handled inside parser_service)
        structured = parse_resume_text(raw_text)
        logger.info(f"AI parsing completed for resume {file.filename}")

        # ✅ Store file in GridFS
        user_id = str(current_user["_id"])
        resume_id = await fs.upload_from_stream(file.filename, io.BytesIO(contents))
        logger.info(f"Stored resume in GridFS (resume_id={resume_id}) for user {user_id}")

        # ✅ Update/replace user’s last resume reference
        await resumes_collection.update_one(
            {"user_id": user_id},
            {"$set": {"resume_file_id": resume_id, "filename": file.filename}},
            upsert=True
        )
        logger.info(f"Updated resume reference in database for user {user_id}")

        return {
            "resume_text": raw_text[:1000],  # preview of extracted text
            "parsed": structured,            # structured JSON from AI
            "resume_id": str(resume_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Resume parsing failed for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Resume parsing failed: {str(e)}")
    finally:
        try:
            if tmp_path:
                import os
                os.unlink(tmp_path)
                logger.debug(f"Temporary file deleted: {tmp_path}")
        except Exception as e:
            logger.warning(f"Could not delete temporary file {tmp_path}: {e}")


# 📥 Download resume (get file back)
@router.get("/download/{resume_id}")
async def download_resume(resume_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"User {current_user['_id']} requested download for resume: {resume_id}")
    try:
        oid = ObjectId(resume_id)
        stream = await fs.open_download_stream(oid)
        logger.info(f"✅ Streaming resume file for user {current_user['_id']}")
        return StreamingResponse(stream, media_type="application/octet-stream")
    except Exception as e:
        logger.error(f"❌ Resume download failed for {resume_id}: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Resume not found: {str(e)}")


# 🗑️ Delete resume
@router.delete("/delete/{resume_id}")
async def delete_resume(resume_id: str, current_user: dict = Depends(get_current_user)):
    logger.info(f"User {current_user['_id']} requested resume deletion: {resume_id}")
    try:
        oid = ObjectId(resume_id)
        await fs.delete(oid)

        # also remove from resumes_collection
        await resumes_collection.delete_one({"user_id": str(current_user["_id"]), "resume_file_id": oid})
        logger.info(f"✅ Resume deleted successfully: {resume_id} (user={current_user['_id']})")

        return {"message": "Resume deleted successfully"}
    except Exception as e:
        logger.error(f"❌ Resume delete failed for {resume_id}: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Resume delete failed: {str(e)}")
