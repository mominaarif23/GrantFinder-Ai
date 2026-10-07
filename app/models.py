from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, EmailStr, Field

# ==============================================================================
# Pydantic Schemas for Requests & Responses
# ==============================================================================

class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(default="student", pattern="^(student|founder|admin)$")

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: Optional[bool] = False

class VerifyOtpRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)
    email: Optional[EmailStr] = None

class ResendOtpRequest(BaseModel):
    email: Optional[EmailStr] = None

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=64)
    new_password: str = Field(..., min_length=6)

class ProfileUpdateRequest(BaseModel):
    type: str = Field(..., pattern="^(academic|startup)$")
    major_domain: str = Field(..., min_length=2)
    degree_level_stage: str = Field(..., min_length=2)
    gpa_funding: Optional[str] = None
    country_preference: str = Field(default="Pakistan")
    extra_details: Optional[Dict[str, Any]] = None

class OnboardingProfileRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    role: str = Field(default="student", pattern="^(student|founder)$")
    avatar_url: Optional[str] = None
    major_domain: str = Field(..., min_length=2)
    degree_level_stage: str = Field(..., min_length=2)
    semester_or_funding: Optional[str] = None
    country_preference: str = Field(default="Both")
    notification_preference: str = Field(default="in_app")

class ProfileDetailsUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    type: Optional[str] = None
    major_domain: Optional[str] = None
    degree_level_stage: Optional[str] = None
    semester: Optional[str] = None
    gpa_funding: Optional[str] = None
    country_preference: Optional[str] = "Pakistan"
    notification_preference: Optional[str] = None
    avatar_url: Optional[str] = None
    # Optional fields for better matching
    university: Optional[str] = None
    cgpa: Optional[str] = None
    city: Optional[str] = None
    grad_year: Optional[str] = None
    test_scores: Optional[str] = None
    financial_need: Optional[str] = None
    extra_details: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    track: str = Field(..., pattern="^(scholarship|grant)$")
    country: str = Field(default="Pakistan")
    keyword: Optional[str] = ""
    is_initial: Optional[bool] = False

class SaveOpportunityRequest(BaseModel):
    opportunity_name: str
    opportunity_type: str
    amount: str
    deadline: str
    source_link: str
    match_score: int = 80

class EssayDraftRequest(BaseModel):
    opportunity_name: str
    opportunity_type: str = "scholarship"
    stated_requirements: Optional[str] = "Academic merit, leadership potential, career goals"
    personal_notes: Optional[str] = ""

class PitchDraftRequest(BaseModel):
    opportunity_name: str
    opportunity_type: str = "grant"
    problem_statement: Optional[str] = ""
    solution_summary: Optional[str] = ""
    funding_ask: Optional[str] = ""

class CuratedOpportunityCreate(BaseModel):
    name: str
    type: str
    category: str
    country: str
    amount: str
    deadline: str
    eligibility: str
    source_link: str
    domains: List[str] = []
    stages: List[str] = []

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    plan: str
    created_at: str

class OpportunityCard(BaseModel):
    id: str
    name: str
    type: str  # scholarship or grant
    category: str
    country: str
    amount: str
    deadline: str
    eligibility: str
    source_link: str
    match_score: int
    match_reasons: List[str]
    is_curated: bool = False
    is_locked: bool = False  # True if blurred in free tier after top 3

class AdvisorChatRequest(BaseModel):
    message: Optional[str] = None
    user_message: Optional[str] = None
    user_id: Optional[Union[str, int]] = None
    history: Optional[List[Dict[str, Any]]] = []
    track: Optional[str] = "scholarship"
    session_id: Optional[str] = "default_session"

