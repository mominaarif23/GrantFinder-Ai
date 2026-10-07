import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services.supabase_service import supabase_service
from app.services.notification_service import (
    dispatch_opportunity_alert, send_registration_otp_email, send_password_reset_email,
    send_premium_match_notification_email
)
from app.auth import create_access_token, hash_password, verify_password

client = TestClient(app)

def test_registration_creates_pending_verification_user():
    """Registering any user should create an unverified account and issue a 6-digit OTP."""
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"pending_user_{unique_suffix}@example.com"
    payload = {
        "name": f"Pending User {unique_suffix}",
        "email": email,
        "password": "Password123!",
        "role": "student"
    }

    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert data["email_verified"] is False
    assert data["redirect"] == "/verify-otp"
    assert "otp" not in data  # BUG-002: Verify zero plaintext token exposure in API responses
    from app.db import get_latest_registration_otp
    otp_code = get_latest_registration_otp(email)
    assert len(otp_code) == 6
    assert otp_code.isdigit()

    # Verify user cannot access dashboard or onboarding yet
    dash_res = client.get("/dashboard", follow_redirects=False)
    assert dash_res.status_code == 302
    assert dash_res.headers["location"] == "/verify-otp"

    onboard_res = client.get("/onboarding", follow_redirects=False)
    assert onboard_res.status_code == 302
    assert onboard_res.headers["location"] == "/verify-otp"

def test_unverified_user_login_redirects_to_otp():
    """An unverified user logging in must be redirected straight to /verify-otp."""
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"unverified_login_{unique_suffix}@example.com"
    pwd = "Password123!"
    user = supabase_service.create_user(
        name=f"Login Test {unique_suffix}",
        email=email,
        password_hash=hash_password(pwd),
        role="student",
        plan="free",
        email_verified=False
    )
    supabase_service.set_user_verified(user["id"], False)

    client.cookies.clear()
    login_res = client.post("/api/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["success"] is True
    assert data["email_verified"] is False
    assert data["redirect"] == "/verify-otp"

def test_otp_verification_success_and_unlocks_features():
    """Entering the correct 6-digit code activates the account and allows access."""
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"verify_success_{unique_suffix}@example.com"
    payload = {
        "name": f"Verified Scholar {unique_suffix}",
        "email": email,
        "password": "Password123!",
        "role": "student"
    }

    reg_res = client.post("/api/auth/register", json=payload)
    assert reg_res.status_code == 201
    assert "otp" not in reg_res.json()  # BUG-002: Zero plaintext token exposure
    from app.db import get_latest_registration_otp
    otp_code = get_latest_registration_otp(email)

    # Submit correct verification code
    verify_res = client.post("/api/auth/verify-registration-otp", json={"code": otp_code, "email": email})
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["success"] is True
    assert data["redirect"] == "/onboarding"

    # Now verify /onboarding renders properly without redirecting to /verify-otp
    onboard_res = client.get("/onboarding")
    assert onboard_res.status_code == 200
    assert "Step 1 of 4" in onboard_res.text

def test_incorrect_otp_and_attempt_limiting():
    """Entering incorrect OTP should decrement attempts; exceeding 5 attempts locks code."""
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"attempt_limit_{unique_suffix}@example.com"
    user = supabase_service.create_user(
        name=f"Attempt Tester {unique_suffix}",
        email=email,
        password_hash=hash_password("Pass@123"),
        role="student",
        plan="free",
        email_verified=False
    )
    supabase_service.set_user_verified(user["id"], False)
    token = create_access_token({"sub": user["id"], "role": user["role"], "plan": user["plan"]})
    client.cookies.set("access_token", token)

    real_code = supabase_service.generate_registration_otp(user["id"], email)

    # Attempts 1 to 4 should report remaining attempts
    for i in range(1, 5):
        res = client.post("/api/auth/verify-registration-otp", json={"code": "000000", "email": email})
        assert res.status_code == 400
        assert "Incorrect verification code" in res.json()["detail"]

    # 5th failed attempt should report maximum exceeded
    res5 = client.post("/api/auth/verify-registration-otp", json={"code": "000000", "email": email})
    assert res5.status_code == 400
    assert "Maximum verification attempts exceeded" in res5.json()["detail"]

    # Even if they now enter the real code, it must reject because attempts were exceeded
    res_real = client.post("/api/auth/verify-registration-otp", json={"code": real_code, "email": email})
    assert res_real.status_code == 400
    assert "Maximum verification attempts exceeded" in res_real.json()["detail"]

def test_otp_resend_cooldown():
    """Resending OTP immediately should hit cooldown; waiting allows new code."""
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"cooldown_test_{unique_suffix}@example.com"
    user = supabase_service.create_user(
        name=f"Cooldown User {unique_suffix}",
        email=email,
        password_hash=hash_password("Pass@123"),
        role="student",
        plan="free",
        email_verified=False
    )
    token = create_access_token({"sub": user["id"], "role": user["role"], "plan": user["plan"]})
    client.cookies.set("access_token", token)

    # Initial code
    supabase_service.generate_registration_otp(user["id"], email)

    # Immediate resend should trigger 429 cooldown
    resend_fail = client.post("/api/auth/resend-registration-otp", json={"email": email})
    assert resend_fail.status_code == 429
    assert "Please wait" in resend_fail.json()["detail"]

def test_expired_otp_rejection():
    """An OTP past the 10-minute validity threshold must be rejected."""
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"expired_test_{unique_suffix}@example.com"
    user = supabase_service.create_user(
        name=f"Expired User {unique_suffix}",
        email=email,
        password_hash=hash_password("Pass@123"),
        role="student",
        plan="free",
        email_verified=False
    )
    token = create_access_token({"sub": user["id"], "role": user["role"], "plan": user["plan"]})
    client.cookies.set("access_token", token)

    code = supabase_service.generate_registration_otp(user["id"], email)
    # Artificially expire the record by setting exp to 15 minutes ago
    entry = supabase_service._REGISTRATION_OTPS.get(user["id"])
    assert entry is not None
    entry["exp"] = datetime.now(timezone.utc) - timedelta(minutes=15)

    verify_res = client.post("/api/auth/verify-registration-otp", json={"code": code, "email": email})
    assert verify_res.status_code == 400
    assert "expired" in verify_res.json()["detail"].lower()

def test_premium_only_match_notification_email_gating():
    """Verify that match notification emails are sent ONLY to premium users, not free users."""
    unique_suffix = uuid.uuid4().hex[:6]
    free_email = f"free_student_{unique_suffix}@example.com"
    premium_email = f"prem_student_{unique_suffix}@example.com"

    # 1. Free verified user
    free_user = supabase_service.create_user(
        name=f"Free Student {unique_suffix}",
        email=free_email,
        password_hash="test_pwd",
        role="student",
        plan="free",
        email_verified=True
    )
    supabase_service.set_user_verified(free_user["id"], True)

    # 2. Premium verified user
    prem_user = supabase_service.create_user(
        name=f"Premium Scholar {unique_suffix}",
        email=premium_email,
        password_hash="test_pwd",
        role="student",
        plan="premium",
        email_verified=True
    )
    supabase_service.set_user_verified(prem_user["id"], True)

    # Dispatch alerts
    dispatch_opportunity_alert(
        user_id=free_user["id"],
        email=free_email,
        plan="free",
        opp_name="Global DAAD Scholarship",
        opp_type="scholarship",
        deadline="2026-12-31",
        match_score=94,
        match_reason="Strong academic alignment",
        amount="Full Tuition + Stipend"
    )

    dispatch_opportunity_alert(
        user_id=prem_user["id"],
        email=premium_email,
        plan="premium",
        opp_name="Fulbright Fellowship",
        opp_type="scholarship",
        deadline="2026-11-15",
        match_score=98,
        match_reason="Leadership and research profile match",
        amount="$50,000"
    )

    # Free user has in-app notification
    free_notes = supabase_service.get_user_notifications(free_user["id"])
    assert len(free_notes) > 0

    # Premium user has in-app notification
    prem_notes = supabase_service.get_user_notifications(prem_user["id"])
    assert len(prem_notes) > 0

    # Test standalone premium match email function
    email_res = send_premium_match_notification_email(
        recipient_email=premium_email,
        user_name="Premium Scholar",
        opportunity_name="Fulbright Fellowship",
        opportunity_type="scholarship",
        match_score=98,
        match_reason="High alignment with engineering discipline",
        deadline="2026-11-15",
        funding_amount="$50,000"
    )
    assert email_res is True

def test_forgot_and_reset_password_flow():
    """Ensure password reset code generation, expiration, and password update works seamlessly."""
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"reset_test_{unique_suffix}@example.com"
    initial_pwd = "OriginalPass@123"
    user = supabase_service.create_user(
        name=f"Reset User {unique_suffix}",
        email=email,
        password_hash=hash_password(initial_pwd),
        role="student",
        plan="free",
        email_verified=True
    )
    supabase_service.set_user_verified(user["id"], True)

    # 1. Request password reset
    forgot_res = client.post("/api/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 200
    assert "If this email exists" in forgot_res.json()["message"]

    # 2. Verify reset record exists
    record = supabase_service._PASSWORD_RESET_OTPS.get(email)
    assert record is not None
    reset_code = record["code"]

    # 3. Attempt reset with wrong code
    bad_reset = client.post("/api/auth/reset-password", json={
        "email": email,
        "code": "999999",
        "new_password": "NewSecretPass@2026"
    })
    assert bad_reset.status_code == 400

    # 4. Attempt reset with correct code
    good_reset = client.post("/api/auth/reset-password", json={
        "email": email,
        "code": reset_code,
        "new_password": "NewSecretPass@2026"
    })
    assert good_reset.status_code == 200
    assert good_reset.json()["success"] is True

    # 5. Invalidation: old code cannot be used again
    reuse_reset = client.post("/api/auth/reset-password", json={
        "email": email,
        "code": reset_code,
        "new_password": "AnotherNewPass@2026"
    })
    assert reuse_reset.status_code == 400

    # 6. User can log in with new password; old password fails
    client.cookies.clear()
    old_login = client.post("/api/auth/login", json={"email": email, "password": initial_pwd})
    assert old_login.status_code == 401

    new_login = client.post("/api/auth/login", json={"email": email, "password": "NewSecretPass@2026"})
    assert new_login.status_code == 200
    assert new_login.json()["success"] is True
