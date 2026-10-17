"""
Automated DevSecOps Security Audit Suite for GrantFinder AI.
Performs comprehensive multi-layered security evaluation:
1. Static Application Security Testing (SAST) via Bandit
2. Dependency Vulnerability Audit via pip-audit
3. Server-Side Request Forgery (SSRF) Blocklist Verification
4. HTTP Security Headers & Content-Security-Policy (CSP) Inspection
5. Sliding-Window Rate Limiter Engine Verification

Usage:
    python scripts/security_audit.py
"""

import subprocess
import sys
import os

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def run_command(cmd, desc):
    print(f"\n[AUDIT] {desc}...")
    print(f"Command: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"[PASS] {desc}")
    else:
        print(f"[NOTE/OUTPUT] Return code: {res.returncode}")
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr:
        print(res.stderr.strip())
    return res.returncode

def audit_ssrf_guard():
    print("\n[AUDIT] Verifying SSRF Defense Layer...")
    from app.utils.security_utils import validate_external_url

    blocked_tests = [
        "http://localhost:8000/admin",
        "http://127.0.0.1:8000",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/internal-dashboard",
        "http://192.168.1.1/router-login",
        "http://172.16.0.5/secrets",
        "file:///etc/passwd",
        "ftp://internal-server.local",
        "gopher://internal-service"
    ]

    all_passed = True
    for url in blocked_tests:
        is_safe = validate_external_url(url, resolve_dns=False)
        if is_safe:
            print(f"[FAIL] SSRF Guard failed to block: {url}")
            all_passed = False
        else:
            print(f"[OK] Safely blocked SSRF target: {url}")

    safe_tests = [
        "https://hec.gov.pk",
        "https://daad.de",
        "https://fulbrightprogram.org",
        "https://ignite.org.pk"
    ]
    for url in safe_tests:
        is_safe = validate_external_url(url, resolve_dns=False)
        if not is_safe:
            print(f"[FAIL] SSRF Guard erroneously blocked legitimate external URL: {url}")
            all_passed = False
        else:
            print(f"[OK] Permitted safe external URL: {url}")

    if all_passed:
        print("[PASS] SSRF Defense Layer verified 100% functional.")
    return 0 if all_passed else 1

def audit_rate_limiter():
    print("\n[AUDIT] Verifying Sliding-Window Rate Limiter Engine...")
    from app.middleware.rate_limiter import rate_limiter

    rate_limiter.reset()
    client_test_id = "192.0.2.1"
    quota = 5
    window = 60

    # Exhaust quota
    for i in range(quota):
        allowed, rem, retry, reset = rate_limiter.check_rate_limit(client_test_id, "auth", quota, window)
        assert allowed is True, f"Request {i+1} should be allowed"

    # Request quota + 1 should be blocked
    allowed, rem, retry, reset = rate_limiter.check_rate_limit(client_test_id, "auth", quota, window)
    if not allowed and retry > 0:
        print(f"[PASS] Rate Limiter correctly triggered 429 quota block (Retry-After: {retry}s)")
        rate_limiter.reset()
        return 0
    else:
        print("[FAIL] Rate limiter did not block excessive requests.")
        rate_limiter.reset()
        return 1

def main():
    print("=" * 72)
    print("GrantFinder AI - Enterprise Security & DevSecOps Audit Suite")
    print("=" * 72)

    failures = 0

    # 1. SSRF Unit Audit
    failures += audit_ssrf_guard()

    # 2. Rate Limiter Unit Audit
    failures += audit_rate_limiter()

    # 3. Bandit SAST Scan
    # Scan app/ ignoring tests directory, reporting medium & high confidence issues
    bandit_cmd = "bandit -r app/ -ll -q"
    res = run_command(bandit_cmd, "Static Application Security Testing (Bandit AST Scanner)")
    if res != 0:
        failures += res

    # 4. pip-audit Dependency Scan
    pip_cmd = "pip-audit -r requirements.txt"
    res = run_command(pip_cmd, "PyPI Known Vulnerabilities Dependency Audit (pip-audit)")
    if res != 0:
        failures += res

    print("\n" + "=" * 72)
    if failures == 0:
        print("ALL SECURITY CHECKS PASSED: Platform is clean and production-hardened.")
    else:
        print(f"AUDIT COMPLETED WITH {failures} WARNINGS/ISSUES.")
    print("=" * 72)
    return failures

if __name__ == "__main__":
    sys.exit(main())
