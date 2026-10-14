"""
Institutional Form and Input Validation Test Suite.
Validates client-side validation asset availability, styling classes,
and server-side RequestValidationError formatting to ensure pristine error messaging.
Strict Zero Emoji Policy.
"""

import os
import re
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_validation_js_asset_integrity():
    """Verify that validation.js exists, contains the core validation engine, and has no emojis."""
    js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js", "validation.js")
    assert os.path.exists(js_path), "validation.js file must exist in static/js"
    
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Assert core functional identifiers exist
    assert "window.GrantFinderValidator" in content
    assert "validateForm" in content
    assert "validateField" in content
    assert "evaluatePasswordStrength" in content
    assert "EMAIL_REGEX" in content
    assert "URL_REGEX" in content
    assert "animate-shake" in content

    # Assert zero emoji policy
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]"
    )
    assert not emoji_pattern.search(content), "validation.js must not contain any emoji"

def test_validation_css_classes():
    """Verify that custom.css defines error, valid, feedback message, and shake animation styles."""
    css_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "css", "custom.css")
    assert os.path.exists(css_path), "custom.css file must exist in static/css"

    with open(css_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert ".input-error" in content
    assert ".input-valid" in content
    assert ".field-error-msg" in content
    assert ".animate-shake" in content
    assert "@keyframes shakeInvalid" in content

def test_base_html_includes_validator():
    """Verify that base.html links validation.js before app.js."""
    resp = client.get("/")
    assert resp.status_code == 200
    text = resp.text
    assert "/static/js/validation.js" in text
    val_idx = text.find("/static/js/validation.js")
    app_idx = text.find("/static/js/app.js")
    assert val_idx != -1 and app_idx != -1
    assert val_idx < app_idx, "validation.js must be loaded prior to app.js"

def test_server_validation_error_formatting_email():
    """Verify that malformed email in registration yields readable detail string instead of raw list."""
    payload = {
        "name": "Institutional Tester",
        "email": "not-a-valid-email",
        "password": "validPassword123",
        "role": "student"
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data
    assert isinstance(data["detail"], str), "detail must be formatted as a string for client toast compatibility"
    assert "Email" in data["detail"] or "email" in data["detail"].lower()
    assert data.get("success") is False

def test_server_validation_error_formatting_password():
    """Verify that password violating minimum length yields clear, human-readable error."""
    payload = {
        "name": "Institutional Tester",
        "email": "test.applicant@university.edu",
        "password": "123",
        "role": "student"
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert isinstance(data["detail"], str)
    assert "Password" in data["detail"]
    assert "6" in data["detail"]

def test_server_validation_error_formatting_role():
    """Verify that an illegal role yields a validation error with descriptive details."""
    payload = {
        "name": "Institutional Tester",
        "email": "test.applicant@university.edu",
        "password": "validPassword123",
        "role": "unauthorized_role"
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert isinstance(data["detail"], str)
    assert "Role" in data["detail"]
