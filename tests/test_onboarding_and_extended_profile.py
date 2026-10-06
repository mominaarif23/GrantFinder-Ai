import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.auth import create_access_token
from app.services.supabase_service import supabase_service
from app.services.curated_service import calculate_base_match_score, generate_match_reasons

client = TestClient(app)

@pytest.fixture
def fresh_user_no_profile():
    """Create a brand new registered user who has not completed onboarding."""
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"onboard_test_{unique_suffix}@example.com"
    user = supabase_service.create_user(
        name=f"New User {unique_suffix}",
        email=email,
        password_hash="test_password_hash",
        role="student",
        plan="free"
    )
    token = create_access_token({"sub": user["id"], "role": user["role"], "plan": user["plan"]})
    return {"user": user, "token": token, "email": email}

def test_onboarding_view_requires_auth():
    """Unauthenticated users should be redirected to login."""
    client.cookies.clear()
    res = client.get("/onboarding", follow_redirects=False)
    assert res.status_code == 302
    assert "/login?next=/onboarding" in res.headers["location"]

def test_onboarding_view_authenticated(fresh_user_no_profile):
    """Authenticated user should be served onboarding.html with wizard elements."""
    client.cookies.set("access_token", fresh_user_no_profile["token"])
    res = client.get("/onboarding")
    assert res.status_code == 200
    html = res.text
    assert "Step 1 of 4" in html
    assert "Select Role Context" in html
    assert "Premium Features & Capabilities" in html
    assert "Future Scope / Roadmap" in html

def test_unonboarded_user_dashboard_redirect(fresh_user_no_profile):
    """Accessing /dashboard without a profile should route directly to /onboarding."""
    client.cookies.set("access_token", fresh_user_no_profile["token"])
    res = client.get("/dashboard", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "/onboarding"

def test_complete_profile_onboarding_student(fresh_user_no_profile):
    """Student onboarding finishes atomically, updates profile and routes to student portal."""
    client.cookies.set("access_token", fresh_user_no_profile["token"])
    payload = {
        "name": "Scholar Candidate",
        "role": "student",
        "avatar_url": "",
        "major_domain": "Biotechnology",
        "degree_level_stage": "Undergraduate BS",
        "semester_or_funding": "4th Semester",
        "country_preference": "Both",
        "notification_preference": "email"
    }
    res = client.post("/api/auth/profile/onboarding", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["redirect_url"] == "/dashboard/student"

    # Profile row now exists in Supabase
    prof = supabase_service.get_profile_by_user_id(fresh_user_no_profile["user"]["id"])
    assert prof is not None
    assert prof["major_domain"] == "Biotechnology"
    assert prof["country_preference"] == "Both"

    # Subsequent dashboard access now redirects to /dashboard/student
    res_dash = client.get("/dashboard", follow_redirects=False)
    assert res_dash.status_code == 302
    assert res_dash.headers["location"] == "/dashboard/student"

def test_complete_profile_onboarding_founder(fresh_user_no_profile):
    """Founder onboarding finishes atomically, updates role to founder and routes to founder portal."""
    client.cookies.set("access_token", fresh_user_no_profile["token"])
    payload = {
        "name": "Founder Candidate",
        "role": "founder",
        "avatar_url": "",
        "major_domain": "ClimateTech",
        "degree_level_stage": "Prototype Stage",
        "semester_or_funding": "$25,000 - $100,000",
        "country_preference": "Pakistan",
        "notification_preference": "in_app"
    }
    res = client.post("/api/auth/profile/onboarding", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["redirect_url"] == "/dashboard/founder"

    fresh_user = supabase_service.get_user_by_id(fresh_user_no_profile["user"]["id"])
    assert fresh_user["role"] == "founder"

def test_update_profile_optional_fields_and_completion_percentage(fresh_user_no_profile):
    """Updating optional fields elevates profile completion percentage up to 100%."""
    client.cookies.set("access_token", fresh_user_no_profile["token"])

    # 1. Onboarding first
    client.post("/api/auth/profile/onboarding", json={
        "name": "Momina Scholar",
        "role": "student",
        "major_domain": "Computer Science",
        "degree_level_stage": "Undergraduate BS",
        "semester_or_funding": "6th Semester",
        "country_preference": "United States",
        "notification_preference": "in_app"
    })

    # Initial profile completion percentage (core baseline >= 60%)
    prof1 = supabase_service.get_profile_by_user_id(fresh_user_no_profile["user"]["id"])
    assert prof1["completion_pct"] >= 60

    # 2. Add optional fields
    opt_payload = {
        "name": "Momina Scholar",
        "university": "NUST Islamabad",
        "cgpa": "3.85",
        "city": "Islamabad",
        "grad_year": "2026",
        "test_scores": "IELTS 8.0",
        "financial_need": "Yes - Partial Need"
    }
    res = client.post("/api/auth/profile/details", json=opt_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True

    prof2 = supabase_service.get_profile_by_user_id(fresh_user_no_profile["user"]["id"])
    assert prof2["university"] == "NUST Islamabad"
    assert prof2["cgpa"] == "3.85"
    assert prof2["city"] == "Islamabad"
    assert prof2["grad_year"] == "2026"
    assert prof2["test_scores"] == "IELTS 8.0"
    assert prof2["completion_pct"] >= 90

def test_curated_match_score_boost_with_optional_fields():
    """Verification that optional profile parameters boost match scores and add specific reasons."""
    opp = {
        "id": "test-opp-1",
        "name": "Global Excellence Scholarship",
        "type": "scholarship",
        "category": "International Fellowship",
        "country": "International",
        "amount": "Partial Tuition",
        "deadline": "2026-05-15",
        "eligibility": "Open to university graduates with demonstrated merit and need.",
        "domains": ["Engineering", "Computer Science"]
    }

    base_profile = {
        "major_domain": "Computer Science",
        "degree_level_stage": "Undergraduate BS",
        "country_preference": "Both"
    }

    enhanced_profile = {
        "major_domain": "Computer Science",
        "degree_level_stage": "Undergraduate BS",
        "country_preference": "Both",
        "university": "NUST",
        "cgpa": "3.9",
        "financial_need": "Yes - Partial Need",
        "test_scores": "TOEFL 105",
        "extra_details": {
            "university": "NUST",
            "cgpa": "3.9",
            "financial_need": "Yes - Partial Need",
            "test_scores": "TOEFL 105"
        }
    }

    base_score = calculate_base_match_score(opp, base_profile, target_country="all")
    enhanced_score = calculate_base_match_score(opp, enhanced_profile, target_country="all")

    assert enhanced_score > base_score, f"Expected boosted score: {enhanced_score} vs {base_score}"

    reasons = generate_match_reasons(opp, enhanced_profile, enhanced_score, target_country="United States")
    joined_reasons = " ".join(reasons)
    assert "Institutional alignment: NUST" in joined_reasons
    assert "Eligible for need-based priority funding allocation" in joined_reasons
    assert "Academic standing (3.9) meets competitive threshold" in joined_reasons
    assert "Language / standardized test profile verified: TOEFL 105" in joined_reasons

def test_founder_onboarding_renders_startup_step3_by_default():
    """Ensure that registering as a founder automatically displays Step 3: Core Startup Details."""
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"founder_wizard_{unique_suffix}@example.com"
    user = supabase_service.create_user(
        name=f"Founder {unique_suffix}",
        email=email,
        password_hash="test_pwd_hash",
        role="founder",
        plan="free"
    )
    token = create_access_token({"sub": user["id"], "role": "founder", "plan": "free"})
    client.cookies.set("access_token", token)

    res = client.get("/onboarding")
    assert res.status_code == 200
    html = res.text
    # Step 3 must render startup details title and description
    assert "Step 3: Core Startup Details" in html
    assert "Specify your startup domain, maturity stage, and target funding amount." in html
    # Student container must be hidden, founder container must NOT be hidden
    assert 'id="studentFieldsContainer" class="hidden space-y-4"' in html
    assert 'id="founderFieldsContainer" class="space-y-4"' in html

def test_founder_profile_management_page_renders_venture_mode():
    """Ensure that the /profile management page renders tailored venture preferences for founders."""
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"founder_prof_{unique_suffix}@example.com"
    user = supabase_service.create_user(
        name=f"Founder {unique_suffix}",
        email=email,
        password_hash="test_pwd_hash",
        role="founder",
        plan="free"
    )
    supabase_service.upsert_profile(
        user_id=user["id"],
        profile_type="startup",
        major_or_domain="FinTech",
        degree_level_or_stage="Prototype / MVP Stage",
        semester="$25,000 - $100,000",
        country_preference="Pakistan"
    )
    token = create_access_token({"sub": user["id"], "role": "founder", "plan": "free"})
    client.cookies.set("access_token", token)

    res = client.get("/profile")
    assert res.status_code == 200
    html = res.text
    assert "Student Founder Venture Preferences" in html
    assert "Startup Domain or Industry Sector" in html
    assert "Venture Maturity Stage" in html
    assert "Funding Target / Capital Ask" in html
    assert "Complete your startup profile for higher grant matching" in html
    assert "University / Incubator Affiliation" in html
