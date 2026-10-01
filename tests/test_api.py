import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def run_init():
    init_db()

def test_landing_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "GrantFinder" in response.text

import uuid

def test_full_student_lifecycle_and_freemium_flow():
    # 1. Register a student user with unique email
    email = f"test.scholar.{uuid.uuid4().hex[:6]}@university.edu"
    reg_payload = {
        "name": "Ayesha Khan",
        "email": email,
        "password": "Password123!",
        "role": "student"
    }
    reg_resp = client.post("/api/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    assert reg_resp.json()["user"]["role"] == "student"
    assert reg_resp.json()["user"]["plan"] == "free"
    
    # 2. Update Student Academic Profile
    prof_payload = {
        "type": "academic",
        "major_domain": "Artificial Intelligence",
        "degree_level_stage": "Undergraduate BS",
        "gpa_funding": "3.85 CGPA",
        "country_preference": "Pakistan"
    }
    prof_resp = client.post("/api/auth/profile", json=prof_payload)
    assert prof_resp.status_code == 200
    assert prof_resp.json()["profile"]["major_domain"] == "Artificial Intelligence"

    # 3. Search Opportunities as Free User (Freemium gating check)
    search_payload = {
        "track": "scholarship",
        "country": "Pakistan",
        "keyword": ""
    }
    search_resp = client.post("/api/opportunities/search", json=search_payload)
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["is_unlimited"] is False
    assert search_data["unlocked_count"] == 3
    assert len(search_data["results"]) > 3
    # Check that first 3 are unlocked and 4th is locked
    assert search_data["results"][0]["is_locked"] is False
    assert search_data["results"][1]["is_locked"] is False
    assert search_data["results"][2]["is_locked"] is False
    assert search_data["results"][3]["is_locked"] is True
    assert "Upgrade to Premium" in search_data["results"][3]["amount"]

    # 4. Attempt AI Essay Drafting as Free User (Must be blocked with 402)
    essay_payload = {
        "opportunity_name": "HEC Indigenous PhD",
        "opportunity_type": "scholarship",
        "stated_requirements": "Academic merit"
    }
    blocked_essay_resp = client.post("/api/assistant/essay", json=essay_payload)
    assert blocked_essay_resp.status_code == 402

    # 5. Execute Mock Upgrade to Premium Tier ($9)
    upgrade_resp = client.post("/api/user/upgrade")
    assert upgrade_resp.status_code == 200
    assert upgrade_resp.json()["plan"] == "premium"

    # 6. Search Opportunities as Premium User (All must be unlocked)
    prem_search_resp = client.post("/api/opportunities/search", json=search_payload)
    assert prem_search_resp.status_code == 200
    prem_search_data = prem_search_resp.json()
    assert prem_search_data["is_unlimited"] is True
    # Confirm card 3 is now unlocked
    assert prem_search_data["results"][3]["is_locked"] is False

    # 7. Execute AI Essay Drafting as Premium User (Must succeed)
    prem_essay_resp = client.post("/api/assistant/essay", json=essay_payload)
    assert prem_essay_resp.status_code == 200
    assert "STATEMENT OF PURPOSE" in prem_essay_resp.json()["essay_draft"]

    # 8. Save Opportunity
    save_payload = {
        "opportunity_name": "HEC Indigenous PhD",
        "opportunity_type": "scholarship",
        "amount": "Full Tuition + Stipend",
        "deadline": "2026-10-31",
        "source_link": "https://hec.gov.pk",
        "match_score": 95
    }
    save_resp = client.post("/api/opportunities/save", json=save_payload)
    assert save_resp.status_code == 200
    saved_id = save_resp.json()["saved"]["id"]

    # 9. List Saved Opportunities
    list_saved_resp = client.get("/api/opportunities/saved")
    assert list_saved_resp.status_code == 200
    assert len(list_saved_resp.json()["saved_opportunities"]) >= 1

    # 10. Delete Saved Opportunity
    del_resp = client.delete(f"/api/opportunities/saved/{saved_id}")
    assert del_resp.status_code == 200

def test_admin_portal_flow():
    # 1. Login as default pre-seeded admin
    login_payload = {
        "email": "admin@grantfinder.ai",
        "password": "AdminPass123!"
    }
    login_resp = client.post("/api/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["role"] == "admin"

    # 2. Access Admin HTML view
    admin_view_resp = client.get("/admin")
    assert admin_view_resp.status_code == 200
    assert "Platform Analytics" in admin_view_resp.text

    # 3. Add a new Curated Opportunity
    curated_payload = {
        "name": "Automated Testing Fellowship 2026",
        "type": "scholarship",
        "category": "Technology",
        "country": "Pakistan",
        "amount": "PKR 2,000,000",
        "deadline": "2026-12-31",
        "eligibility": "Computer Science students",
        "source_link": "https://example.com/test",
        "domains": ["Computer Science"],
        "stages": []
    }
    add_resp = client.post("/api/admin/curated", json=curated_payload)
    assert add_resp.status_code == 200
    created_id = add_resp.json()["created"]["id"]

    # 4. Delete the added opportunity
    del_resp = client.delete(f"/api/admin/curated/{created_id}")
    assert del_resp.status_code == 200
