from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, Optional
from app.models import EssayDraftRequest, PitchDraftRequest, AdvisorChatRequest
from app.db import get_profile_by_user_id
from app.auth import get_current_user, get_current_user_optional, require_verified_user
from app.services.ai_service import generate_scholarship_essay, generate_startup_pitch
from app.services.advisor_service import run_advisor_turn

router = APIRouter(prefix="/api/assistant", tags=["AI Application Assistant"])

@router.post("/chat")
async def chat_with_advisor(
    req: AdvisorChatRequest,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    user_msg = req.user_message or req.message or ""
    if not user_msg.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_message or message field is required"
        )
        
    profile = None
    user_id = req.user_id
    if user:
        user_id = user["id"]
        profile = get_profile_by_user_id(user_id)
    elif req.user_id:
        profile = get_profile_by_user_id(req.user_id)
        
    result = await run_advisor_turn(
        user_message=user_msg,
        chat_history=req.history or [],
        track=req.track or "scholarship",
        profile=profile,
        session_id=req.session_id or f"session_{user_id or 'anon'}",
        user_id=user_id
    )
    return result


@router.post("/essay")
async def create_essay_draft(req: EssayDraftRequest, user: Dict[str, Any] = Depends(require_verified_user)):
    # Freemium gating
    if user.get("plan") != "premium" and user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="The AI Scholarship Essay Assistant is a Premium feature. Upgrade to Premium ($9 demo) to unlock tailored statement drafts."
        )
        
    profile = get_profile_by_user_id(user["id"]) or {
        "major_domain": "General Studies",
        "degree_level_stage": "Undergraduate",
        "country_preference": "Pakistan",
        "gpa_funding": "3.5 CGPA"
    }
    
    essay = await generate_scholarship_essay(
        student_profile=profile,
        opp_name=req.opportunity_name,
        requirements=req.stated_requirements or "Merit, leadership, community commitment",
        personal_notes=req.personal_notes or ""
    )
    
    return {
        "success": True,
        "opportunity_name": req.opportunity_name,
        "essay_draft": essay
    }

@router.post("/pitch")
async def create_pitch_draft(req: PitchDraftRequest, user: Dict[str, Any] = Depends(require_verified_user)):
    # Freemium gating
    if user.get("plan") != "premium" and user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="The AI Startup Grant Pitch Assistant is a Premium feature. Upgrade to Premium ($9 demo) to unlock customized grant proposals."
        )
        
    profile = get_profile_by_user_id(user["id"]) or {
        "major_domain": "Technology & SaaS",
        "degree_level_stage": "Working Prototype",
        "country_preference": "Pakistan",
        "gpa_funding": "PKR 2,500,000"
    }
    
    pitch = await generate_startup_pitch(
        founder_profile=profile,
        grant_name=req.opportunity_name,
        problem_stmt=req.problem_statement or "",
        solution_sum=req.solution_summary or "",
        funding_ask=req.funding_ask or ""
    )
    
    return {
        "success": True,
        "opportunity_name": req.opportunity_name,
        "pitch_draft": pitch
    }
