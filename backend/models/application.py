# backend/models/application.py
from pydantic import BaseModel, HttpUrl
from typing import Literal, Optional, List
from datetime import datetime

class Comment(BaseModel):
    text: str
    timestamp: datetime = datetime.utcnow()

class Application(BaseModel):
    user_id: str
    job_title: str
    company: str
    url: Optional[HttpUrl] = None
    status: Literal["not_submitted", "submitted", "interview", "rejected", "offer"] = "not_submitted"
    applied_on: Optional[datetime] = None
    next_action: Optional[str] = None
    comments: List[Comment] = []
