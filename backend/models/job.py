from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class RealtimeJob(BaseModel):
    source: str
    source_id: str
    title: Optional[str]
    company: Optional[str]
    locations: List[str] = Field(default_factory=list)
    work_modes: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    levels: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    description: Optional[str]
    salary: Optional[Dict[str, Any]] = None
    url: Optional[HttpUrl] = None
    metadata: Optional[Dict[str, Any]] = None
    last_seen_active: datetime
    collected_at: datetime


class RealtimeJobsResponse(BaseModel):
    items: List[RealtimeJob]
    count: int
    page: int
    page_size: int
