from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any, List
from app.models import SearchRequest, SaveOpportunityRequest
from app.db import (
    log_search, save_opportunity, get_saved_opportunities, delete_saved_opportunity,
    update_user_plan, get_profile_by_user_id
)
from app.auth import get_current_user, get_current_user_optional
from app.services.curated_service import get_curated_matches
from app.services.search_service import execute_web_search
from app.services.ai_service import extract_and_structure_web_results
from app.services.notification_service import dispatch_opportunity_alert, send_in_app_notification

router = APIRouter(prefix="/api/opportunities", tags=["Opportunities"])

@router.post("/search")
async def search_opportunities(req: SearchRequest, request: Request):
    user = get_current_user_optional(request)
    user_id = user["id"] if user else None
    user_plan = user.get("plan", "free") if user else "free"
    
    # Get user profile if available
    profile = get_profile_by_user_id(user_id) if user_id else None
    
    # 1. Log search for analytics
    log_search(user_id=user_id, track=req.track, country=req.country, keyword=req.keyword)
    
    # 2. Query Curated Database
    curated_cards = get_curated_matches(track=req.track, country=req.country, profile=profile)
    
    # Filter curated if keyword specified
    if req.keyword and req.keyword.strip():
        kw = req.keyword.lower().strip()
        curated_cards = [
            c for c in curated_cards 
            if kw in c["name"].lower() or kw in c.get("category", "").lower() or kw in c.get("eligibility", "").lower()
        ]
        
    # 3. Query Live Web Search
    raw_web_snippets = await execute_web_search(
        track=req.track, country=req.country, keyword=req.keyword, profile=profile
    )
    
    # 4. Extract and Structure Web Discoveries using AI
    web_cards = await extract_and_structure_web_results(
        raw_snippets=raw_web_snippets, track=req.track, profile=profile
    )
    
    # 5. Merge and rank all results
    all_results = curated_cards + web_cards
    
    # Deduplicate by name similarity
    unique_results = []
    seen_names = set()
    for item in all_results:
        norm_name = "".join(ch for ch in item["name"].lower() if ch.isalnum())
        if norm_name not in seen_names:
            seen_names.add(norm_name)
            unique_results.append(item)
            
    # Sort descending by match score
    unique_results.sort(key=lambda x: x["match_score"], reverse=True)
    
    # 6. Apply Freemium Gating (Top 3 unlocked for free; all unlocked for premium/admin)
    is_premium_or_admin = (user_plan == "premium") or (user and user.get("role") == "admin")
    
    processed_results = []
    for idx, card in enumerate(unique_results):
        card_copy = card.copy()
        if not is_premium_or_admin and idx >= 3:
            card_copy["is_locked"] = True
            card_copy["amount"] = "[Restricted] Upgrade to Premium ($9) to reveal exact grant amount"
            card_copy["eligibility"] = "[Restricted] Full eligibility criteria, application checklist, and AI essay/pitch drafting require Premium access."
            card_copy["source_link"] = "#upgrade"
        else:
            card_copy["is_locked"] = False
        processed_results.append(card_copy)
        
    return {
        "success": True,
        "track": req.track,
        "country": req.country,
        "plan": user_plan,
        "total_found": len(unique_results),
        "unlocked_count": len(unique_results) if is_premium_or_admin else min(3, len(unique_results)),
        "is_unlimited": is_premium_or_admin,
        "results": processed_results
    }

@router.post("/save")
def save_user_opportunity(req: SaveOpportunityRequest, user: Dict[str, Any] = Depends(get_current_user)):
    saved = save_opportunity(
        user_id=user["id"],
        name=req.opportunity_name,
        otype=req.opportunity_type,
        amount=req.amount,
        deadline=req.deadline,
        source_link=req.source_link,
        match_score=req.match_score
    )
    
    # Dispatch notification alert
    dispatch_opportunity_alert(
        user_id=user["id"],
        email=user["email"],
        plan=user["plan"],
        opp_name=req.opportunity_name,
        opp_type=req.opportunity_type,
        deadline=req.deadline,
        match_score=req.match_score
    )
    
    return {"success": True, "saved": saved}

@router.get("/saved")
def list_user_saved(user: Dict[str, Any] = Depends(get_current_user)):
    items = get_saved_opportunities(user["id"])
    return {"success": True, "saved_opportunities": items}

@router.delete("/saved/{saved_id}")
def remove_saved(saved_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    delete_saved_opportunity(user_id=user["id"], saved_id=saved_id)
    return {"success": True, "message": "Saved opportunity removed"}

@router.post("/upgrade")
def mock_upgrade_plan(user: Dict[str, Any] = Depends(get_current_user)):
    update_user_plan(user["id"], "premium")
    send_in_app_notification(
        user_id=user["id"],
        title="Welcome to Premium Tier",
        message="Your $9 lifetime upgrade was processed. You now have unlimited opportunity matches, AI application essay & pitch draft tools, and instant WhatsApp alerts."
    )
    return {
        "success": True,
        "message": "Successfully upgraded to Premium plan.",
        "plan": "premium"
    }
