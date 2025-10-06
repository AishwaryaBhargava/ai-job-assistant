from pydantic import BaseModel, EmailStr, HttpUrl
from typing import List, Optional

# Shared fields for all user-related models
class UserBase(BaseModel):
    name: str
    email: EmailStr

# For registration (auth)
class UserRegister(UserBase):
    password: str   # plain text on input, will be hashed before storing

# For login
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Work experience details
class WorkExperience(BaseModel):
    company: str
    role: str
    duration: str       # ✅ replaced years with duration
    location: str
    tasks: str          # ✅ free text string (e.g., "Built backend APIs, managed deployments")

# Education details
class Education(BaseModel):
    degree: str
    school: str
    year: str           # ✅ string for flexibility
    gpa: str            # ✅ GPA included

# Extended profile (resume-like info)
class UserProfile(UserBase):
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    twitter: Optional[str] = None
    portfolio: Optional[str] = None
    location: Optional[str] = None
    websites: Optional[List[str]] = []
    resume_file: Optional[dict] = None
    skills: List[str] = []
    work_experience: Optional[List[WorkExperience]] = []
    education: Optional[List[Education]] = []


# Representation of user stored in DB (with hashed password)
class UserInDB(UserProfile):
    hashed_password: str
