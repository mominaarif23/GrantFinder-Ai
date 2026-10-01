import pytest
from app.db import init_db
from app.services.curated_service import get_curated_matches, calculate_base_match_score
from app.services.search_service import execute_web_search, generate_mock_web_results
from app.services.ai_service import (
    extract_and_structure_web_results, 
    generate_scholarship_essay, 
    generate_startup_pitch
)
from app.services.notification_service import send_in_app_notification

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

@pytest.mark.asyncio
async def test_curated_matches_scholarship():
    profile = {
        "major_domain": "Computer Science",
        "degree_level_stage": "Undergraduate BS",
        "country_preference": "Pakistan"
    }
    matches = get_curated_matches(track="scholarship", country="Pakistan", profile=profile)
    assert len(matches) > 0
    first = matches[0]
    assert first["type"] == "scholarship"
    assert first["is_curated"] is True
    assert first["match_score"] >= 75
    assert len(first["match_reasons"]) > 0

@pytest.mark.asyncio
async def test_curated_matches_grant():
    profile = {
        "major_domain": "Artificial Intelligence",
        "degree_level_stage": "Working Prototype",
        "country_preference": "Pakistan"
    }
    matches = get_curated_matches(track="grant", country="Pakistan", profile=profile)
    assert len(matches) > 0
    first = matches[0]
    assert first["type"] == "grant"
    assert first["is_curated"] is True

@pytest.mark.asyncio
async def test_live_search_fallback():
    profile = {"major_domain": "Data Science", "country_preference": "Pakistan"}
    results = await execute_web_search(track="scholarship", country="Pakistan", keyword="AI", profile=profile)
    assert len(results) > 0
    assert "title" in results[0]
    assert "link" in results[0]

@pytest.mark.asyncio
async def test_ai_structuring_and_drafting():
    snippets = [
        {
            "title": "HEC Need Based Scholarship 2026",
            "snippet": "Full tuition and PKR 50,000 monthly allowance for students with 3.2 CGPA. Deadline November 15, 2026.",
            "link": "https://hec.gov.pk",
            "source": "HEC"
        }
    ]
    cards = await extract_and_structure_web_results(snippets, track="scholarship")
    assert len(cards) == 1
    assert cards[0]["name"] == "HEC Need Based Scholarship 2026"
    assert cards[0]["match_score"] >= 65

    # Test Essay Drafting
    student_profile = {
        "major_domain": "Software Engineering",
        "degree_level_stage": "Undergraduate BS",
        "country_preference": "Pakistan",
        "gpa_funding": "3.8 CGPA"
    }
    essay = await generate_scholarship_essay(student_profile, "Fulbright Pakistan", "Leadership", "Robotics club president")
    assert "STATEMENT OF PURPOSE" in essay
    assert "Software Engineering" in essay

    # Test Pitch Drafting
    founder_profile = {
        "major_domain": "AgriTech",
        "degree_level_stage": "Working Prototype",
        "country_preference": "Pakistan",
        "gpa_funding": "PKR 4,000,000"
    }
    pitch = await generate_startup_pitch(founder_profile, "Ignite SEED Grant", "Crop disease detection delay", "Drone multispectral imaging", "PKR 4,000,000")
    assert "STARTUP INNOVATION GRANT PROPOSAL" in pitch
    assert "AgriTech" in pitch
