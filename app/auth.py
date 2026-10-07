import os
import hashlib
import hmac
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from app.config import settings
from app.db import get_user_by_id, get_avatar_url

# ==============================================================================
# Password Hashing & Verification (Cryptographically secure PBKDF2-HMAC-SHA256)
# ==============================================================================

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100_000
    ).hex()
    return f"{salt}${pwd_hash}"

def verify_password(password: str, hashed_str: str) -> bool:
    try:
        salt, expected_hash = hashed_str.split("$")
        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100_000
        ).hex()
        return hmac.compare_digest(expected_hash, computed_hash)
    except Exception:
        return False

# ==============================================================================
# JWT Generation & Decoding
# ==============================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except (jwt.PyJWTError, Exception):
        return None

# ==============================================================================
# Auth Dependencies for FastAPI
# ==============================================================================

def get_token_from_request(request: Request) -> Optional[str]:
    # 1. Check Authorization Bearer header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1].strip()
    # 2. Check HTTP-only Cookie
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        if cookie_token.startswith("Bearer "):
            return cookie_token.split(" ")[1].strip()
        return cookie_token.strip()
    return None

def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    token = get_token_from_request(request)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user = get_user_by_id(payload["sub"])
    if user:
        user["avatar_url"] = get_avatar_url(user["id"])
        user["email_verified"] = is_user_email_verified(user)
    return user

def is_user_email_verified(user: Optional[Dict[str, Any]]) -> bool:
    """Check whether user has completed email verification."""
    if not user:
        return False
    from app.services.supabase_service import supabase_service
    if user.get("role") == "admin":
        return True
    return supabase_service.is_user_verified(user.get("id")) or supabase_service.is_user_verified(user.get("email"))

def get_current_user(request: Request) -> Dict[str, Any]:
    user = get_current_user_optional(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in to proceed.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def require_verified_user(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Strict backend gate enforcing that email_verified must be True."""
    if not is_user_email_verified(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="EMAIL_NOT_VERIFIED",
            headers={"X-Redirect-URL": "/verify-otp"}
        )
    return user

def require_role(allowed_roles: list):
    def role_checker(user: Dict[str, Any] = Depends(require_verified_user)) -> Dict[str, Any]:
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {allowed_roles}"
            )
        return user
    return role_checker

def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required."
        )
    return user

def require_premium(user: Dict[str, Any] = Depends(require_verified_user)) -> Dict[str, Any]:
    if user.get("plan") != "premium" and user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Premium tier required to unlock this feature."
        )
    return user
