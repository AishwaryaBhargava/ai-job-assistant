from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ScoreItem(BaseModel):
    requirement: str
    critical: bool
    matched_text: Optional[str] = None
    similarity: Optional[float] = None


class ScoreDimension(BaseModel):
    score: int
    applicable: bool
    matched: List[ScoreItem]
    missing: List[ScoreItem]


class ScoreBreakdown(BaseModel):
    skills: ScoreDimension
    experience: ScoreDimension
    education: ScoreDimension
    keywords: ScoreDimension


class ResumeAnalysisResult(BaseModel):
    overall_score: int
    breakdown: ScoreBreakdown
    suggestions: List[str]
    weights: Dict[str, float]
    resume_snapshot: Optional[Dict[str, Any]] = None
    job_requirements: Optional[Dict[str, Any]] = None


class Resume(BaseModel):
    user_id: Optional[str] = None
    resume_text: str
    analysis_result: Optional[ResumeAnalysisResult] = None


class ResumeAnalysis(BaseModel):
    user_id: Optional[str] = None
    resume_text: Optional[str] = None
    job_description: Optional[str] = None
    analysis_result: Dict[str, Any]
    created_at: Optional[datetime] = None
    resume_source: Optional[str] = "text"
    resume_filename: Optional[str] = None
    resume_file_id: Optional[str] = None


