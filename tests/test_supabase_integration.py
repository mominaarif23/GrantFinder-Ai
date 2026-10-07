import pytest
import uuid
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.services.supabase_service import supabase_service
from app.services.notification_service import notify_user

client = TestClient(app)

@pytest.mark.asyncio
async def test_supabase_live_registration_and_table_presence():
    """
    Verification Test 1 from Supabase Integration Plan:
    Register a test account through POST /api/auth/register.
    Verify row is inserted directly into Supabase public.users.
    """
    unique_suffix = str(uuid.uuid4())[:8]
    test_email = f"scholar.{unique_suffix}@grantfinder.ai"
    reg_payload = {
        "name": f"Verified Scholar {unique_suffix}",
        "email": test_email,
        "password": "SecurePassword123!",
        "role": "student"
    }

    # 1. Register through API
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 201, f"Registration failed: {res.text}"
    data = res.json()
    assert data["success"] is True
    user_id = data["user"]["id"]
    token = data["token"]
    assert user_id, "User ID was not returned"

    # 2. Query Supabase directly via REST API to verify presence in public.users
    user_record = supabase_service.get_user_by_email(test_email)
    assert user_record is not None, "User record was not found in Supabase public.users"
    assert user_record["id"] == user_id
    assert user_record["email"] == test_email
    assert user_record["role"] == "student"
    assert user_record["plan"] == "free"

    # Mark user as verified to access protected endpoints
    supabase_service.set_user_verified(user_id, True)

    # 3. Verify user profile upsert writes to Supabase public.profiles
    prof_payload = {
        "type": "academic",
        "major_domain": "Software Engineering",
        "degree_level_stage": "Undergraduate BS",
        "gpa_funding": "3.85 CGPA",
        "country_preference": "Germany"
    }
    prof_res = client.post(
        "/api/auth/profile",
        json=prof_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert prof_res.status_code == 200
    
    # Query Supabase public.profiles directly
    prof_record = supabase_service.get_profile_by_user_id(user_id)
    assert prof_record is not None, "Profile record not found in Supabase public.profiles"
    assert prof_record["user_id"] == user_id
    assert prof_record["major_or_domain"] == "Software Engineering"
    assert prof_record["country_preference"] == "Germany"

@pytest.mark.asyncio
async def test_supabase_freemium_notification_channels():
    """
    Verification Test 2 from Supabase Integration Plan:
    - Free user trigger -> in_app and email created, whatsapp skipped.
    - Premium user trigger -> all three (in_app, email, whatsapp) created.
    """
    unique_suffix = str(uuid.uuid4())[:8]
    test_email = f"notify.{unique_suffix}@grantfinder.ai"
    reg_payload = {
        "name": f"Notify User {unique_suffix}",
        "email": test_email,
        "password": "Password123!",
        "role": "student"
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_id = reg_res.json()["user"]["id"]

    # Confirm double opt-in subscription to enable email channel
    supabase_service.set_email_subscription(user_id, True)

    # Free user alert dispatch
    notify_user(user_id=user_id, message="Test free alert message", event_type="match")
    free_notifs = supabase_service.get_user_notifications(user_id)
    free_channels = [n.get("channel") for n in free_notifs]
    assert "in_app" in free_channels, "in_app channel missing for free user"
    assert "email" not in free_channels, "email channel should be restricted to premium users"
    assert "whatsapp" not in free_channels, "whatsapp should NOT be recorded for free user"

    # Upgrade to premium
    supabase_service.update_user_plan(user_id, "premium")
    prem_user = supabase_service.get_user_by_id(user_id)
    assert prem_user["plan"] == "premium"

    # Premium user alert dispatch
    notify_user(user_id=user_id, message="Test premium alert message", event_type="deadline")
    prem_notifs = supabase_service.get_user_notifications(user_id)
    prem_channels = [n.get("channel") for n in prem_notifs]
    assert "in_app" in prem_channels
    assert "email" in prem_channels
    assert "whatsapp" in prem_channels, "whatsapp channel missing for premium user"

@pytest.mark.asyncio
async def test_supabase_saved_opportunities_and_curated():
    """
    Verification Test 3 from Supabase Integration Plan:
    Verify curated opportunities exist in Supabase and saving an opportunity persists to public.saved_opportunities.
    """
    # 1. Verify curated opportunities in Supabase
    curated = supabase_service.list_curated_opportunities()
    assert len(curated) >= 20, f"Expected >= 20 curated opportunities in Supabase, found {len(curated)}"

    # 2. Register user to test saved opportunity
    unique_suffix = str(uuid.uuid4())[:8]
    test_email = f"saver.{unique_suffix}@grantfinder.ai"
    reg_payload = {
        "name": f"Saver {unique_suffix}",
        "email": test_email,
        "password": "Password123!",
        "role": "student"
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    token = reg_res.json()["token"]
    user_id = reg_res.json()["user"]["id"]
    supabase_service.set_user_verified(user_id, True)

    # 3. Save opportunity via API
    opp_payload = {
        "opportunity_name": "Chevening UK Government Scholarships",
        "opportunity_type": "scholarship",
        "amount": "Full Tuition + Living",
        "deadline": "2026-11-05",
        "source_link": "https://www.chevening.org",
        "match_score": 90
    }
    save_res = client.post(
        "/api/opportunities/save",
        json=opp_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert save_res.status_code == 200

    # 4. Verify in Supabase public.saved_opportunities
    saved = supabase_service.get_saved_opportunities(user_id)
    assert len(saved) >= 1
    assert any(s["opportunity_name"] == "Chevening UK Government Scholarships" for s in saved)
