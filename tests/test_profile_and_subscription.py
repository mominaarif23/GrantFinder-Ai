import pytest
import io
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.auth import create_access_token
from app.services.supabase_service import supabase_service
from app.services.notification_service import notify_user
from app.services.search_service import execute_web_search
from app.services.ai_service import extract_and_structure_web_results
from app.services.curated_service import get_curated_matches, calculate_base_match_score

client = TestClient(app)

@pytest.fixture
def auth_user():
    """Create a verified test user with JWT cookie for authentication tests."""
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"profile_test_{unique_suffix}@example.com"
    user = supabase_service.create_user(
        name=f"Profile Tester {unique_suffix}",
        email=email,
        password_hash="test_hash_val",
        role="student",
        plan="free"
    )
    token = create_access_token({"sub": user["id"], "role": user["role"], "plan": user["plan"]})
    return {"user": user, "token": token, "email": email}

# ==============================================================================
# Module A: Profile Management & Supabase Storage Avatars
# ==============================================================================

def test_avatar_upload_file_type_validation(auth_user):
    """Ensure non-image formats are rejected with HTTP 400."""
    client.cookies.set("access_token", auth_user["token"])

    # Attempt to upload PDF file
    pdf_bytes = b"%PDF-1.4 Fake PDF file content"
    files = {"file": ("malicious.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res = client.post("/api/auth/profile/avatar", files=files)
    assert res.status_code == 400
    assert "Invalid image format" in res.json()["detail"]

    # Attempt to upload EXE binary
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00"
    files = {"file": ("virus.exe", io.BytesIO(exe_bytes), "application/x-msdownload")}
    res = client.post("/api/auth/profile/avatar", files=files)
    assert res.status_code == 400

def test_avatar_upload_file_size_validation(auth_user):
    """Ensure payloads > 2MB are rejected with HTTP 400."""
    client.cookies.set("access_token", auth_user["token"])

    # Create oversized image dummy payload (2.5MB)
    large_payload = b"\x89PNG\r\n\x1a\n" + (b"0" * (2500 * 1024))
    files = {"file": ("large_photo.png", io.BytesIO(large_payload), "image/png")}
    res = client.post("/api/auth/profile/avatar", files=files)
    assert res.status_code == 400
    assert "exceeds maximum allowable size of 2MB" in res.json()["detail"]

def test_avatar_upload_and_delete_flow(auth_user):
    """Ensure valid image <= 2MB uploads to Supabase Storage and deletion works cleanly."""
    client.cookies.set("access_token", auth_user["token"])

    # 1. Valid PNG upload
    valid_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    files = {"file": ("avatar.png", io.BytesIO(valid_png), "image/png")}
    res = client.post("/api/auth/profile/avatar", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    avatar_url = data["avatar_url"]
    assert "avatar.png" in avatar_url

    # 2. Verify avatar appears in /api/auth/me
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["user"]["avatar_url"] == avatar_url

    # 3. Delete avatar
    del_res = client.delete("/api/auth/profile/avatar")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 4. Verify /api/auth/me returns empty or null avatar
    me_after = client.get("/api/auth/me")
    assert not me_after.json()["user"]["avatar_url"]

def test_profile_view_and_details_update(auth_user):
    """Ensure /profile HTML renders and /api/auth/profile/details updates credentials."""
    client.cookies.set("access_token", auth_user["token"])

    # 1. Render GET /profile
    view_res = client.get("/profile")
    assert view_res.status_code == 200
    assert "Account & Opportunity Profile" in view_res.text
    assert "Profile Picture" in view_res.text
    assert "Academic & Venture Preferences" in view_res.text

    # 2. Update details
    new_name = "Updated Scholar Name"
    payload = {
        "name": new_name,
        "email": auth_user["email"],
        "type": "academic",
        "major_domain": "Biomedical Engineering",
        "degree_level_stage": "Doctoral PhD",
        "gpa_funding": "3.9 CGPA",
        "country_preference": "Germany"
    }
    update_res = client.post("/api/auth/profile/details", json=payload)
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["success"] is True
    assert data["user"]["name"] == new_name
    assert data["profile"]["major_domain"] == "Biomedical Engineering"
    assert data["profile"]["degree_level_stage"] == "Doctoral PhD"

def test_portal_navbar_avatar_persistence(auth_user):
    """Ensure user avatar picture remains visible in navbar when returning to student or founder portals."""
    client.cookies.set("access_token", auth_user["token"])
    
    # 1. Upload valid avatar
    dummy_img = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    upload_res = client.post("/api/auth/profile/avatar", files={"file": ("avatar.png", io.BytesIO(dummy_img), "image/png")})
    assert upload_res.status_code == 200
    avatar_url = upload_res.json()["avatar_url"]
    assert avatar_url
    
    # 2. Complete onboarding profile so dashboard allows access
    client.post("/api/auth/profile/onboarding", json={
        "name": auth_user["user"]["name"],
        "role": "student",
        "avatar_url": avatar_url,
        "major_domain": "Computer Science",
        "degree_level_stage": "Undergraduate BS",
        "semester_or_funding": "6th Semester",
        "country_preference": "Both",
        "notification_preference": "in_app"
    })
    
    # 3. Check /profile renders avatar image
    profile_res = client.get("/profile")
    assert profile_res.status_code == 200
    assert avatar_url in profile_res.text
    
    # 4. Check /dashboard/student renders avatar image in navbar and does NOT hide it
    student_res = client.get("/dashboard/student")
    assert student_res.status_code == 200
    assert avatar_url in student_res.text
    assert f'src="{avatar_url}"' in student_res.text

# ==============================================================================
# Module B: Universal Major & Domain Matching Engine (4 Unseen Domains)
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("domain,track,target_country", [
    ("Biomedical Engineering", "scholarship", "Germany"),
    ("Fashion Design", "scholarship", "France"),
    ("Agritech", "grant", "Pakistan"),
    ("FinTech", "grant", "United Kingdom"),
])
async def test_universal_domain_matching_generalization(domain, track, target_country):
    """
    Validate that search, extraction, and semantic scoring work seamlessly
    across 4 previously untested free-text domains without hardcoded domain lists.
    """
    profile = {
        "major_domain": domain,
        "degree_level_stage": "Master's Degree" if track == "scholarship" else "Early Prototype MVP",
        "country_preference": target_country,
        "gpa_funding": "3.8 CGPA"
    }

    # 1. Web search index generation incorporates domain
    results = await execute_web_search(track=track, country=target_country, profile=profile)
    assert len(results) > 0

    # Verify domain token is reflected in snippet contents
    combined_snippets = " ".join([r.get("snippet", "") + " " + r.get("title", "") for r in results])
    domain_tokens = domain.lower().split()
    assert any(tok in combined_snippets.lower() for tok in domain_tokens), f"Domain token '{domain}' not found in search results"

    # 2. Extraction and heuristic structuring
    cards = await extract_and_structure_web_results(results, track=track, profile=profile, country=target_country)
    assert len(cards) > 0
    top_card = cards[0]
    assert top_card["match_score"] >= 70
    assert any("discipline" in r.lower() or "domain" in r.lower() or domain.lower() in r.lower() or "technical" in r.lower() for r in top_card["match_reasons"])

    # 3. Base matching score evaluation
    sample_opp = {
        "name": f"{target_country} International Excellence Fund",
        "country": target_country,
        "domains": [domain, "Science & Engineering"],
        "category": "Fellowship",
        "eligibility": f"Applicants in {domain} are highly encouraged to apply.",
        "amount": "$25,000"
    }
    score = calculate_base_match_score(sample_opp, profile, target_country=target_country)
    assert score >= 80

# ==============================================================================
# Module C: Double Opt-In Email Notifications & Anti-Spam Gate
# ==============================================================================

def test_double_optin_token_and_verification_flow(auth_user):
    """Test cryptographic token generation and verification for confirm/unsubscribe."""
    user_id = auth_user["user"]["id"]
    email = auth_user["email"]

    # Generate token
    token = supabase_service.generate_subscription_token(user_id=user_id, email=email, action="confirm")
    assert isinstance(token, str) and len(token) > 20

    # Verify valid token
    payload = supabase_service.verify_subscription_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["email"] == email.lower()
    assert payload["action"] == "confirm"

    # Verify corrupted token
    invalid_payload = supabase_service.verify_subscription_token("invalid.jwt.token")
    assert invalid_payload is None

def test_double_optin_email_gating_and_delivery_lifecycle(auth_user):
    """
    Verify complete anti-spam double opt-in lifecycle:
    1. Newly registered user starts with email_subscribed = False.
    2. Automated email notifications are strictly suppressed.
    3. User confirms via token endpoint -> email_subscribed becomes True.
    4. Automated email notifications are dispatched.
    5. User unsubscribes via unsubscribe link -> email_subscribed becomes False.
    6. Automated email notifications are suppressed again.
    """
    user_id = auth_user["user"]["id"]
    email = auth_user["email"]

    # 1. Initially unconfirmed
    assert supabase_service.is_email_subscribed(user_id) is False

    # 2. Dispatch automated alert: Only in_app should be recorded
    notify_user(user_id=user_id, message="Alert 1: Pre-confirmation test", event_type="match")
    notifs_1 = supabase_service.get_user_notifications(user_id)
    channels_1 = [n.get("channel") for n in notifs_1]
    assert "in_app" in channels_1
    assert "email" not in channels_1, "Automated email sent before double opt-in confirmation!"

    # 3. User clicks confirmation link in email
    confirm_token = supabase_service.generate_subscription_token(user_id=user_id, email=email, action="confirm")
    confirm_res = client.get(f"/api/notifications/confirm-email?token={confirm_token}")
    assert confirm_res.status_code in (200, 302)
    assert supabase_service.is_email_subscribed(user_id) is True

    # 4. Dispatch automated alert: Both in_app and email should be recorded
    notify_user(user_id=user_id, message="Alert 2: Post-confirmation test", event_type="deadline")
    notifs_2 = supabase_service.get_user_notifications(user_id)
    channels_2 = [n.get("channel") for n in notifs_2]
    assert "in_app" in channels_2
    assert "email" in channels_2, "Email notification suppressed even after opt-in confirmed!"

    # 5. User clicks unsubscribe link in notification email
    unsub_token = supabase_service.generate_subscription_token(user_id=user_id, email=email, action="unsubscribe")
    unsub_res = client.get(f"/api/notifications/unsubscribe?token={unsub_token}")
    assert unsub_res.status_code == 200
    assert "Unsubscribed Successfully" in unsub_res.text
    assert supabase_service.is_email_subscribed(user_id) is False

    # 6. Dispatch automated alert again: Email should be suppressed again
    # Clear notifs or count new email rows
    pre_email_count = sum(1 for n in supabase_service.get_user_notifications(user_id) if n.get("channel") == "email")
    notify_user(user_id=user_id, message="Alert 3: Post-unsub test", event_type="match")
    post_email_count = sum(1 for n in supabase_service.get_user_notifications(user_id) if n.get("channel") == "email")
    assert post_email_count == pre_email_count, "Email notification sent after unsubscribing!"

def test_resend_confirmation_endpoint(auth_user):
    """Test that POST /api/notifications/resend-confirmation dispatches confirmation email."""
    client.cookies.set("access_token", auth_user["token"])
    res = client.post("/api/notifications/resend-confirmation")
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert "dispatched" in res.json()["message"]


def test_dark_mode_theme_toggle_elements_and_markup(auth_user):
    """
    Verify that Dark Mode (Night Theme) elements and configuration are present:
    1. Tailwind config includes darkMode: 'class'.
    2. Theme toggle button (#themeToggleBtn) and sun/moon SVG icons exist in navbar.
    3. Mobile theme toggle button exists in mobile drawer.
    4. Inline FOUC prevention script is in <head>.
    5. Custom CSS contains institutional dark mode rules.
    6. App.js contains toggleThemeMode and syncThemeIcons handlers.
    """
    # 1. Landing page check
    landing_res = client.get("/")
    assert landing_res.status_code == 200
    landing_html = landing_res.text
    assert "darkMode: 'class'" in landing_html
    assert 'id="themeToggleBtn"' in landing_html
    assert 'id="themeSunIcon"' in landing_html
    assert 'id="themeMoonIcon"' in landing_html
    assert "toggleThemeMode()" in landing_html
    assert "grantfinder_theme" in landing_html

    # 2. Portal & Profile check
    client.cookies.set("access_token", auth_user["token"])
    profile_res = client.get("/profile")
    assert profile_res.status_code == 200
    assert 'id="themeToggleBtn"' in profile_res.text

    portal_res = client.get("/dashboard/student")
    assert portal_res.status_code == 200
    assert 'id="themeToggleBtn"' in portal_res.text

    # 3. CSS dark mode rules check
    css_res = client.get("/static/css/custom.css")
    assert css_res.status_code == 200
    assert "html.dark" in css_res.text
    assert "color-scheme: dark" in css_res.text

    # 4. JS theme toggle script check
    js_res = client.get("/static/js/app.js")
    assert js_res.status_code == 200
    assert "function toggleThemeMode" in js_res.text
    assert "function syncThemeIcons" in js_res.text


def test_email_otp_generation_and_verification_flow(auth_user):
    """
    Verify 6-digit OTP email verification flow:
    1. Unverified user initially has email_subscribed == False.
    2. Resend confirmation dispatches email with a 6-digit numeric OTP.
    3. Profile page renders 6-digit OTP input (#emailOtpInput) and verify button.
    4. Submitting invalid OTP returns 400.
    5. Submitting correct OTP marks email_subscribed == True.
    """
    user_id = auth_user["user"]["id"]
    email = auth_user["email"]

    # 1. Reset subscription to False
    supabase_service.set_email_subscription(user_id, False)
    assert supabase_service.is_email_subscribed(user_id) is False

    # 2. Generate OTP
    otp = supabase_service.generate_email_otp(user_id, email)
    assert len(otp) == 6
    assert otp.isdigit()

    # 3. Check profile page markup for OTP controls
    client.cookies.set("access_token", auth_user["token"])
    prof_res = client.get("/profile")
    assert prof_res.status_code == 200
    assert 'id="emailOtpInput"' in prof_res.text
    assert 'id="verifyOtpBtn"' in prof_res.text

    # 4. Test invalid OTP submission
    bad_res = client.post("/api/notifications/verify-otp", json={"otp": "000000"})
    assert bad_res.status_code == 400
    assert "Invalid or expired" in bad_res.json()["detail"]
    assert supabase_service.is_email_subscribed(user_id) is False

    # 5. Test valid OTP submission
    good_res = client.post("/api/notifications/verify-otp", json={"otp": otp})
    assert good_res.status_code == 200
    assert good_res.json()["success"] is True
    assert supabase_service.is_email_subscribed(user_id) is True


def test_smtp_bounce_guard_for_test_domains():
    """
    Verify that notification service intercepts dummy/test domains (@grantfinder.ai, @example.com),
    preventing real SMTP network socket calls and avoiding Mailer-Daemon delivery failure bounce emails.
    """
    from app.services.notification_service import send_smtp_email
    
    # Should safely return True without throwing or attempting SMTP connection
    assert send_smtp_email("test.student@grantfinder.ai", "Test Subject", "Test Body") is True
    assert send_smtp_email("applicant@example.com", "Test Subject", "Test Body") is True
    assert send_smtp_email("user@test.com", "Test Subject", "Test Body") is True


def test_enterprise_footer_elements_and_lines():
    """
    Verify that the enhanced enterprise 4-column footer architecture is present:
    1. Weekly Opportunity Digest newsletter strip with email input and submit button.
    2. Operational Platform Status indicator badge ("All Systems Operational").
    3. Opportunity Tracks, Platform Capabilities, and Verified Portals columns.
    4. Bottom legal disclosures and architectural divider lines.
    """
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Newsletter / Alert strip
    assert 'id="footerNewsletterForm"' in html
    assert 'id="footerNewsletterEmail"' in html
    assert 'id="footerNewsletterBtn"' in html
    assert "Weekly Opportunity Digest" in html

    # Operational status
    assert "All Systems Operational" in html

    # 4 columns & links
    assert "Opportunity Tracks" in html
    assert "Platform Capabilities" in html
    assert "Verified Portals" in html
    assert "HEC Higher Education Commission" in html
    assert "Ignite National Technology Fund" in html
    assert "DAAD Germany Exchange Service" in html
    assert "Double Opt-In Anti-Spam Guarantee" in html


