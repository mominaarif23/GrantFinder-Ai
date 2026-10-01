import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.config import settings
from app.services.supabase_service import supabase_service

# In-memory analytics tracker for live session activity
_SEARCH_LOGS: List[Dict[str, Any]] = []

def init_db():
    """Initialize database connection to Supabase and seed baseline data."""
    # 1. Verify live connectivity to Supabase
    health = supabase_service.check_health_sync()
    
    # 2. Seed curated opportunities if table is empty
    curated = supabase_service.list_curated_opportunities()
    if len(curated) == 0:
        seed_curated_data()
        
    # 3. Seed default admin user if not present
    admin_user = supabase_service.get_user_by_email("admin@grantfinder.ai")
    if not admin_user:
        from app.auth import hash_password
        supabase_service.create_user(
            name="System Administrator",
            email="admin@grantfinder.ai",
            password_hash=hash_password("AdminPass123!"),
            role="admin",
            plan="premium"
        )
        
    # 4. Seed Momina account if not present
    momina_user = supabase_service.get_user_by_email("momnaaa23@gmail.com")
    if not momina_user:
        from app.auth import hash_password
        u = supabase_service.create_user(
            name="Momina",
            email="momnaaa23@gmail.com",
            password_hash=hash_password("Password123!"),
            role="student",
            plan="premium"
        )
        supabase_service.upsert_profile(
            user_id=u["id"],
            profile_type="academic",
            major_or_domain="IT",
            degree_level_or_stage="Undergraduate BS",
            semester="6th Semester",
            country_preference="United States"
        )

def seed_curated_data():
    """Seed the curated scholarships and innovation grants from JSON into Supabase."""
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "curated_opportunities.json")
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            items = json.load(f)
            for item in items:
                try:
                    supabase_service.add_curated_opportunity(item)
                except Exception:
                    pass

# ==============================================================================
# Direct Supabase Database Operations (Single Source of Truth)
# ==============================================================================

def create_user(name: str, email: str, password_hash: str, role: str = "student", plan: str = "free") -> Dict[str, Any]:
    """Create a new user directly in Supabase public.users."""
    return supabase_service.create_user(
        name=name, email=email, password_hash=password_hash, role=role, plan=plan
    )

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve user from Supabase public.users by email."""
    return supabase_service.get_user_by_email(email)

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user from Supabase public.users by id."""
    return supabase_service.get_user_by_id(user_id)

def update_user_plan(user_id: str, new_plan: str) -> bool:
    """Update user subscription plan in Supabase public.users."""
    return supabase_service.update_user_plan(user_id, new_plan)

def list_all_users() -> List[Dict[str, Any]]:
    """List all users directly from Supabase public.users."""
    return supabase_service.list_all_users()

def get_profile_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Query user profile from Supabase public.profiles."""
    return supabase_service.get_profile_by_user_id(user_id)

def upsert_profile(
    user_id: str,
    ptype: str,
    major_domain: str,
    degree_level_stage: str, 
    gpa_funding: Optional[str] = None,
    country_preference: str = "Pakistan",
    extra_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Upsert profile directly into Supabase public.profiles."""
    return supabase_service.upsert_profile(
        user_id=user_id,
        profile_type=ptype,
        major_or_domain=major_domain,
        degree_level_or_stage=degree_level_stage,
        semester=gpa_funding,
        country_preference=country_preference,
        gpa_funding=gpa_funding,
        extra_details=extra_details
    )

def list_curated_opportunities(track: Optional[str] = None, country: Optional[str] = None) -> List[Dict[str, Any]]:
    """List curated opportunities from Supabase public.curated_opportunities."""
    return supabase_service.list_curated_opportunities(track=track, country=country)

def add_curated_opportunity(data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert curated opportunity into Supabase public.curated_opportunities."""
    return supabase_service.add_curated_opportunity(data)

def delete_curated_opportunity(opp_id: str) -> bool:
    """Delete curated opportunity from Supabase public.curated_opportunities."""
    return supabase_service.delete_curated_opportunity(opp_id)

def save_opportunity(
    user_id: str,
    name: str,
    otype: str,
    amount: str,
    deadline: str,
    source_link: str,
    match_score: int
) -> Dict[str, Any]:
    """Save opportunity into Supabase public.saved_opportunities."""
    return supabase_service.save_opportunity(
        user_id=user_id,
        opportunity_name=name,
        source_link=source_link,
        match_score=match_score,
        opportunity_type=otype,
        amount=amount,
        deadline=deadline
    )

def get_saved_opportunities(user_id: str) -> List[Dict[str, Any]]:
    """Query saved opportunities from Supabase public.saved_opportunities."""
    return supabase_service.get_saved_opportunities(user_id)

def delete_saved_opportunity(user_id: str, saved_id: str) -> bool:
    """Delete saved opportunity from Supabase public.saved_opportunities."""
    return supabase_service.delete_saved_opportunity(user_id, saved_id)

def add_notification(user_id: str, title: str, message: str, channel: str = "in_app") -> Dict[str, Any]:
    """Insert notification into Supabase public.notifications."""
    formatted = f"{title}: {message}" if title else message
    return supabase_service.insert_notification(user_id=user_id, message=formatted, channel=channel)

def get_user_notifications(user_id: str) -> List[Dict[str, Any]]:
    """Query notifications from Supabase public.notifications."""
    return supabase_service.get_user_notifications(user_id)

def mark_notification_read(notification_id: str, user_id: Optional[str] = None) -> bool:
    """Mark notification read in Supabase public.notifications."""
    return supabase_service.mark_notification_read(notification_id, user_id)

def log_search(user_id: Optional[str], track: str, country: str, keyword: Optional[str]):
    """Log search event for real-time analytics."""
    _SEARCH_LOGS.append({
        "user_id": user_id,
        "track": track,
        "country": country,
        "keyword": keyword or "",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

def get_platform_analytics() -> Dict[str, Any]:
    """Calculate platform analytics directly from Supabase and live telemetry."""
    users = supabase_service.list_all_users()
    total_users = len(users)
    premium_users = len([u for u in users if u.get("plan") == "premium"])
    
    country_counts: Dict[str, int] = {}
    track_counts: Dict[str, int] = {}
    for l in _SEARCH_LOGS:
        c = l.get("country", "Pakistan")
        t = l.get("track", "scholarship")
        country_counts[c] = country_counts.get(c, 0) + 1
        track_counts[t] = track_counts.get(t, 0) + 1

    top_countries = [
        {"country": k, "cnt": v} 
        for k, v in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    track_breakdown = [{"track": k, "cnt": v} for k, v in track_counts.items()]

    return {
        "total_users": total_users,
        "premium_users": premium_users,
        "total_searches": len(_SEARCH_LOGS),
        "total_saved": 0,
        "top_countries": top_countries or [{"country": "Pakistan", "cnt": 1}],
        "track_breakdown": track_breakdown or [{"track": "scholarship", "cnt": 1}]
    }
