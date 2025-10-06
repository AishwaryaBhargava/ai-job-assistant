from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WeakSection(BaseModel):
    section: str
    issue: str
    evidence: Optional[str] = None


class PhrasingSuggestion(BaseModel):
    original: str
    improved: str
    reason: Optional[str] = None


class MissingKeywords(BaseModel):
    role_family: Optional[str] = None
    must_have: List[str] = Field(default_factory=list)
    nice_to_have: List[str] = Field(default_factory=list)


class QuickFix(BaseModel):
    title: str
    description: str
    impact: str = Field(pattern="^(High|Medium|Low)$")
    effort_minutes: int = Field(ge=0)


class ResumeReviewResult(BaseModel):
    ats_score: int = Field(default=0, ge=0, le=100)
    summary_headline: str = ""
    overall_feedback: str = ""
    weak_sections: List[WeakSection] = Field(default_factory=list)
    phrasing_suggestions: List[PhrasingSuggestion] = Field(default_factory=list)
    missing_keywords: MissingKeywords = Field(default_factory=MissingKeywords)
    quick_fixes: List[QuickFix] = Field(default_factory=list)
    resume_snapshot: Dict[str, Any] = Field(default_factory=dict)


class ResumeReview(BaseModel):
    user_id: Optional[str] = None
    resume_text: Optional[str] = None
    resume_source: str = "text"
    resume_filename: Optional[str] = None
    resume_file_id: Optional[str] = None
    review_result: Dict[str, Any]
    ats_score_cache: Optional[int] = None
    quick_fix_titles: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None



