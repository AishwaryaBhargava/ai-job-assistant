import re
import docx
try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None
try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None
try:
    import win32com.client as win32
except ImportError:
    win32 = None
from services.ai_service import parse_resume_with_ai
from utils.logger import logger


def sanitize_text(text: str) -> str:
    logger.info("Sanitizing extracted text")
    
    try:
        if not text:
            logger.info("Text is empty, returning empty string")
            return ""
        
        cleaned = text.replace("\ufffd", " ")
        cleaned = re.sub(r"[\t\x0b\x0c\r]+", " ", cleaned)
        cleaned = re.sub(r"[ ]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        result = cleaned.strip()
        
        logger.info(f"✅ Text sanitized successfully (length: {len(result)} chars)")
        return result
    
    except Exception as e:
        logger.error(f"❌ Failed to sanitize text: {e}", exc_info=True)
        raise


def extract_text_from_file(file_path: str) -> str:
    """Extract raw text from supported resume file formats."""
    logger.info(f"Extracting text from file: {file_path}")
    
    try:
        suffix = file_path.lower()
        
        if suffix.endswith(".pdf"):
            logger.info("Processing PDF file")
            
            if fitz is not None:
                logger.info("Using PyMuPDF (fitz) for PDF extraction")
                with fitz.open(file_path) as pdf:
                    raw = "\n".join(page.get_text("text") or "" for page in pdf)
                    result = sanitize_text(raw)
                    logger.info(f"✅ PDF text extracted successfully using PyMuPDF ({len(result)} chars)")
                    return result
            
            if pdfplumber is not None:
                logger.info("Using pdfplumber for PDF extraction")
                with pdfplumber.open(file_path) as pdf:
                    raw = "\n".join(page.extract_text() or "" for page in pdf.pages)
                    result = sanitize_text(raw)
                    logger.info(f"✅ PDF text extracted successfully using pdfplumber ({len(result)} chars)")
                    return result
            
            logger.warning("No PDF extraction library available")
            raise ValueError("PDF extraction requires PyMuPDF (`pip install pymupdf`) or pdfplumber.")
        
        if suffix.endswith(".docx"):
            logger.info("Processing DOCX file")
            doc = docx.Document(file_path)
            raw = "\n".join(p.text for p in doc.paragraphs)
            result = sanitize_text(raw)
            logger.info(f"✅ DOCX text extracted successfully ({len(result)} chars)")
            return result
        
        if suffix.endswith(".txt"):
            logger.info("Processing TXT file")
            with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                raw = handle.read()
            result = sanitize_text(raw)
            logger.info(f"✅ TXT text extracted successfully ({len(result)} chars)")
            return result
        
        if suffix.endswith(".rtf"):
            logger.info("Processing RTF file")
            with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                raw = handle.read()
            text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", raw)
            text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", text)
            text = text.replace("{", " ").replace("}", " ")
            result = sanitize_text(text)
            logger.info(f"✅ RTF text extracted successfully ({len(result)} chars)")
            return result
        
        if suffix.endswith(".doc"):
            logger.info("Processing legacy DOC file")
            
            if win32 is None:
                logger.warning("pywin32 not available for legacy DOC file")
                raise ValueError(
                    "Legacy .doc resumes require Microsoft Word (pywin32). Please convert to PDF, DOCX, TXT, or RTF."
                )
            
            word = win32.Dispatch("Word.Application")
            word.Visible = False
            try:
                doc_obj = word.Documents.Open(file_path)
                raw = doc_obj.Content.Text
                doc_obj.Close()
            finally:
                word.Quit()
            result = sanitize_text(raw)
            logger.info(f"✅ DOC text extracted successfully ({len(result)} chars)")
            return result
        
        logger.warning(f"Unsupported file format: {suffix}")
        raise ValueError("Unsupported resume format.")
    
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to extract text from file {file_path}: {e}", exc_info=True)
        raise


def parse_resume_text(text: str) -> dict:
    """Use AI to turn raw resume text into structured fields."""
    logger.info("Parsing resume text with AI")
    
    try:
        result = parse_resume_with_ai(text)
        logger.info(f"✅ Resume text parsed successfully")
        return result
    
    except Exception as exc:
        logger.error(f"❌ AI parsing failed: {exc}", exc_info=True)
        return {
            "name": "",
            "email": "",
            "phone": "",
            "linkedin": "",
            "github": "",
            "twitter": "",
            "portfolio": "",
            "location": "",
            "websites": [],
            "skills": [],
            "education": [],
            "work_experience": [],
            "error": f"AI parsing failed: {exc}",
        }