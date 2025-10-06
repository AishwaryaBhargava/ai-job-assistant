from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PreferencePayload(BaseModel):
    values: List[str] = Field(default_factory=list, max_items=3)
    role_families: List[str] = Field(default_factory=list, max_items=5)
    specializations: List[str] = Field(default_factory=list, max_items=5)
    locations: List[str] = Field(default_factory=list)
    remote_ok: bool = False
    seniority_levels: List[str] = Field(default_factory=list, max_items=2)
    leadership_preference: Optional[str] = None
    company_sizes: List[str] = Field(default_factory=list)
    industries_like: List[str] = Field(default_factory=list)
    industries_avoid: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    disliked_skills: List[str] = Field(default_factory=list)
    min_salary: Optional[int] = Field(default=None, ge=0)
    currency: str = "USD"
    job_search_status: Optional[str] = None


class PreferenceResponse(PreferencePayload):
    updated_at: Optional[datetime] = None


class GuestRecommendationRequest(BaseModel):
    preferences: PreferencePayload
    resume_snippets: Optional[List[str]] = None
    limit: int = Field(default=20, ge=1, le=50)

