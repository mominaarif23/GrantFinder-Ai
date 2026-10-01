from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Response, Request, Depends
from typing import Dict, Any
from app.models import UserRegisterRequest, UserLoginRequest, ProfileUpdateRequest, UserResponse
from app.db import (
    create_user, get_user_by_email, get_user_by_id, upsert_profile, 
    get_profile_by_user_id
)
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, response: Response):
    existing = get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")
    
    pwd_hash = hash_password(req.password)
    user = create_user(name=req.name, email=req.email, password_hash=pwd_hash, role=req.role, plan="free")
    
    # Auto-login: issue JWT cookie
    token = create_access_token({"sub": user["id"], "role": user["role"], "plan": user["plan"]})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax"
    )
    
    return {
        "success": True,
        "message": "Registration successful",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "plan": user["plan"]
        },
        "token": token
    }

@router.post("/login")
def login(req: UserLoginRequest, response: Response):
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    # Extended 30-day session if remember_me is requested, otherwise standard 1 day (86400s)
    if req.remember_me:
        delta = timedelta(days=30)
        cookie_max_age = 30 * 86400
    else:
        delta = timedelta(days=1)
        cookie_max_age = 86400

    token = create_access_token({"sub": user["id"], "role": user["role"], "plan": user["plan"]}, expires_delta=delta)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=cookie_max_age,
        samesite="lax"
    )
    
    return {
        "success": True,
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "plan": user["plan"]
        },
        "token": token
    }

@router.post("/logout")
@router.get("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"success": True, "message": "Logged out successfully"}

@router.get("/me")
def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    profile = get_profile_by_user_id(user["id"])
    return {
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "plan": user["plan"],
            "created_at": user["created_at"]
        },
        "profile": profile
    }

@router.post("/profile")
def update_profile(req: ProfileUpdateRequest, user: Dict[str, Any] = Depends(get_current_user)):
    updated = upsert_profile(
        user_id=user["id"],
        ptype=req.type,
        major_domain=req.major_domain,
        degree_level_stage=req.degree_level_stage,
        gpa_funding=req.gpa_funding,
        country_preference=req.country_preference,
        extra_details=req.extra_details
    )
    return {"success": True, "profile": updated}
