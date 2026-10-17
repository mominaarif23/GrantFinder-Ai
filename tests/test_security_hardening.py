import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.middleware.rate_limiter import rate_limiter
from app.utils.security_utils import validate_external_url, sanitize_html_input, mask_ip_for_logs

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_limiter_before_test():
    """Ensure in-memory rate limiter is reset cleanly before and after each test."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()

def test_security_headers_and_csp_enforcement():
    """Verify that every response carries institutional HTTP security headers and CSP."""
    res = client.get("/")
    assert res.status_code == 200

    headers = res.headers
    # Content Security Policy
    assert "content-security-policy" in headers
    csp = headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "https://cdn.tailwindcss.com" in csp
    assert "https://fonts.googleapis.com" in csp
    assert "frame-ancestors 'none'" in csp

    # Anti-Clickjacking & MIME protections
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-content-type-options") == "nosniff"

    # Transport Security & Referrer
    assert "max-age=31536000" in headers.get("strict-transport-security", "")
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    # Modern Permissions & Isolation
    assert "camera=()" in headers.get("permissions-policy", "")
    assert headers.get("cross-origin-opener-policy") == "same-origin"
    assert headers.get("cross-origin-resource-policy") == "same-origin"

def test_csrf_origin_verification_blocks_unauthorized_domains():
    """Verify that state-changing requests from unauthorized foreign origins are rejected with 403."""
    # 1. State-changing request from unauthorized foreign origin -> Blocked
    foreign_res = client.post(
        "/api/auth/login",
        json={"email": "attacker@evil.com", "password": "Password123!"},
        headers={"Origin": "https://malicious-attacker.com"}
    )
    assert foreign_res.status_code == 403
    assert "CSRF" in foreign_res.json()["detail"]

    # 2. State-changing request with matching or local origin -> Permitted past CSRF check
    allowed_res = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@grantfinder.ai", "password": "Password123!"},
        headers={"Origin": "http://testserver"}
    )
    assert allowed_res.status_code != 403

def test_sliding_window_rate_limiter_auth_tier():
    """Verify that rapid requests to authentication endpoints trigger 429 Too Many Requests."""
    rate_limiter.reset()
    client_ip_header = {"X-Forwarded-For": "198.51.100.10"}

    # Auth tier has a quota of 5 requests per 60 seconds
    for _ in range(5):
        res = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "WrongPassword"},
            headers=client_ip_header
        )
        assert res.status_code in (400, 401, 422)

    # 6th request within window must be throttled with HTTP 429
    blocked_res = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "WrongPassword"},
        headers=client_ip_header
    )
    assert blocked_res.status_code == 429
    assert "Rate limit exceeded" in blocked_res.json()["detail"]
    assert "retry_after" in blocked_res.json()
    assert "retry-after" in blocked_res.headers
    assert blocked_res.headers.get("x-ratelimit-remaining") == "0"

def test_sliding_window_rate_limiter_otp_tier():
    """Verify that OTP verification endpoints enforce strict 5 req/min rate limit."""
    rate_limiter.reset()
    client_ip_header = {"X-Forwarded-For": "198.51.100.20"}

    # Exhaust OTP quota (5 requests)
    for _ in range(5):
        res = client.post(
            "/api/notifications/verify-otp",
            json={"email": "test@example.com", "otp": "000000"},
            headers=client_ip_header
        )
        assert res.status_code in (400, 422)

    # 6th request must trigger 429
    blocked = client.post(
        "/api/notifications/verify-otp",
        json={"email": "test@example.com", "otp": "000000"},
        headers=client_ip_header
    )
    assert blocked.status_code == 429
    assert int(blocked.headers.get("retry-after", "0")) > 0

def test_ssrf_validator_blocks_internal_and_cloud_metadata():
    """Verify that Server-Side Request Forgery validator catches internal subnets and metadata APIs."""
    # Disallowed targets
    assert validate_external_url("http://127.0.0.1:8000/admin", resolve_dns=False) is False
    assert validate_external_url("http://localhost:5000", resolve_dns=False) is False
    assert validate_external_url("http://169.254.169.254/latest/meta-data/", resolve_dns=False) is False
    assert validate_external_url("http://10.0.0.50/dashboard", resolve_dns=False) is False
    assert validate_external_url("http://192.168.1.1/api", resolve_dns=False) is False
    assert validate_external_url("http://172.16.0.1/status", resolve_dns=False) is False
    assert validate_external_url("file:///etc/shadow", resolve_dns=False) is False
    assert validate_external_url("ftp://internal.repo", resolve_dns=False) is False
    assert validate_external_url("", resolve_dns=False) is False

    # Allowed targets
    assert validate_external_url("https://hec.gov.pk", resolve_dns=False) is True
    assert validate_external_url("https://daad.de/en/", resolve_dns=False) is True
    assert validate_external_url("https://fulbrightprogram.org", resolve_dns=False) is True

def test_health_probes_liveness_and_readiness():
    """Verify production health check, liveness probe, and readiness probe."""
    # 1. General health summary
    h_res = client.get("/health")
    assert h_res.status_code == 200
    assert h_res.json()["status"] == "healthy"
    assert h_res.json()["app"] == "GrantFinder AI"

    # 2. Liveness probe (Kubernetes / Render orchestrator)
    l_res = client.get("/health/live")
    assert l_res.status_code == 200
    assert l_res.json()["status"] == "alive"

    # 3. Readiness probe
    r_res = client.get("/health/ready")
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "ready"
    assert r_res.json()["database_ready"] is True

def test_html_sanitizer_prevents_xss():
    """Verify that user input sanitization neutralizes HTML and script tags."""
    malicious_payload = "<script>alert('XSS Attack');</script>"
    sanitized = sanitize_html_input(malicious_payload)
    assert "<script>" not in sanitized
    assert "&lt;script&gt;" in sanitized
    assert sanitize_html_input(None) == ""

def test_ip_masking_for_privacy_logs():
    """Verify IP masking for GDPR/compliance privacy logs."""
    assert mask_ip_for_logs("192.168.1.150") == "192.168.1.***"
    assert mask_ip_for_logs("2001:0db8:85a3:0000:0000:8a2e:0370:7334").startswith("2001:0db8:****")
    assert mask_ip_for_logs("localhost") == "localhost"
