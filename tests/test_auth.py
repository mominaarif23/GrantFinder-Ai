import pytest
from app.auth import hash_password, verify_password, create_access_token, decode_access_token

def test_password_hashing():
    pwd = "SecureStudentPass2026!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert "$" in hashed
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False

def test_jwt_token_flow():
    payload = {"sub": "user-test-123", "role": "student", "plan": "free"}
    token = create_access_token(payload)
    assert isinstance(token, str)
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-test-123"
    assert decoded["role"] == "student"
    assert decoded["plan"] == "free"

def test_jwt_invalid_token():
    decoded = decode_access_token("invalid.token.structure")
    assert decoded is None

def test_jwt_remember_me_extended_token():
    from datetime import timedelta
    payload = {"sub": "user-remember-456", "role": "founder", "plan": "premium"}
    # 30-day extended expiration
    token = create_access_token(payload, expires_delta=timedelta(days=30))
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-remember-456"
    assert decoded["exp"] > decoded.get("iat", 0) + (29 * 86400)

