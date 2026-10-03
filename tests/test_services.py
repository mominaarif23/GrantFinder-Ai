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

@pytest.mark.asyncio
async def test_germany_search_relevance_and_no_pakistan_default():
    """
    Verifies that when a user searches for Germany:
    1. Top 3 results are relevant to Germany or European programs (e.g. DAAD, Deutschlandstipendium).
    2. Domestic Pakistani scholarships (LUMS, NUST, FAST) are strictly excluded from Germany results.
    """
    student_profile = {
        "major_domain": "Computer Science",
        "degree_level_stage": "Master's Degree",
        "country_preference": "Germany",
        "gpa_funding": "3.8 CGPA"
    }

    # Curated matches
    curated = get_curated_matches(track="scholarship", country="Germany", profile=student_profile)
    # Check DAAD is present and top ranked
    curated_names = [c["name"].lower() for c in curated]
    assert any("daad" in n or "germany" in n or "erasmus" in n for n in curated_names)
    assert not any("lums" in n or "peef" in n or "ehsaas" in n for n in curated_names)

    # Web search matches
    web_results = await execute_web_search(track="scholarship", country="Germany", keyword="", profile=student_profile)
    assert len(web_results) > 0
    web_cards = await extract_and_structure_web_results(web_results, track="scholarship", profile=student_profile, country="Germany")
    
    # Check all web cards for Germany have country Germany and high match score
    for card in web_cards:
        assert card["country"] == "Germany"
        assert card["match_score"] >= 80

    # Combined top 3
    combined = curated + web_cards
    combined.sort(key=lambda x: x["match_score"], reverse=True)
    top_3 = combined[:3]
    top_3_names = [c["name"].lower() for c in top_3]
    assert not any("lums" in n or "nust" in n or "fast" in n for n in top_3_names)

@pytest.mark.asyncio
async def test_expanded_countries_web_coverage():
    """
    Verifies that European countries and China return country-targeted opportunities.
    """
    for country in ["China", "France", "United Kingdom", "Sweden", "Netherlands"]:
        results = await execute_web_search(track="scholarship", country=country, keyword="", profile={"major_domain": "Artificial Intelligence"})
        assert len(results) > 0
        cards = await extract_and_structure_web_results(results, track="scholarship", country=country)
        assert len(cards) > 0
        assert cards[0]["country"] == country

@pytest.mark.asyncio
async def test_whatsapp_notification_dispatch():
    """
    Verifies that WhatsApp dispatch succeeds via Meta Cloud API / CallMeBot / simulation fallback
    without requiring twilio.
    """
    from app.services.notification_service import send_whatsapp_message
    success = send_whatsapp_message("+923001234567", "Test priority alert")
    assert success is True

