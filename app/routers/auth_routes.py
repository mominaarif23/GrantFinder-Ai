from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Response, Request, Depends, UploadFile, File, BackgroundTasks
from typing import Dict, Any, Optional
import os
from app.models import (
    UserRegisterRequest, UserLoginRequest, ProfileUpdateRequest, 
    ProfileDetailsUpdateRequest, UserResponse
)
from app.db import (
    create_user, get_user_by_email, get_user_by_id, upsert_profile, 
    get_profile_by_user_id, upload_avatar, delete_avatar, get_avatar_url,
    update_user_details
)
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.services.notification_service import send_optin_confirmation_email

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, response: Response, background_tasks: BackgroundTasks):
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

    # Dispatch double opt-in verification email in background
    try:
        background_tasks.add_task(
            send_optin_confirmation_email,
            user_id=user["id"],
            recipient_email=user["email"],
            user_name=user.get("name", "Applicant")
        )
    except Exception:
        pass
    
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
    avatar = (profile and profile.get("avatar_url")) or get_avatar_url(user["id"])
    return {
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "plan": user["plan"],
            "created_at": user.get("created_at"),
            "avatar_url": avatar
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

@router.post("/profile/avatar")
async def upload_user_avatar(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user)
):
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
    ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
    
    filename = file.filename or "avatar.png"
    _, ext = os.path.splitext(filename.lower())
    
    if ext not in ALLOWED_EXTS or file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format. Supported formats: JPG, PNG, WEBP."
        )
    
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Image file exceeds maximum allowable size of 2MB."
        )
    
    clean_ext = ext.lstrip(".")
    avatar_url = upload_avatar(
        user_id=user["id"],
        file_bytes=contents,
        file_ext=clean_ext,
        content_type=file.content_type or "image/png"
    )
    
    # Persist avatar URL in user profile
    upsert_profile(user_id=user["id"], avatar_url=avatar_url)
    
    return {
        "success": True,
        "avatar_url": avatar_url,
        "message": "Profile picture updated successfully."
    }

@router.delete("/profile/avatar")
def delete_user_avatar(user: Dict[str, Any] = Depends(get_current_user)):
    delete_avatar(user["id"])
    upsert_profile(user_id=user["id"], avatar_url="")
    return {
        "success": True,
        "message": "Profile picture removed successfully."
    }

@router.post("/profile/details")
def update_profile_details(
    req: ProfileDetailsUpdateRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    # 1. Update user credentials (name / email) if changed
    if req.name or req.email:
        update_user_details(
            user_id=user["id"],
            name=req.name,
            email=str(req.email) if req.email else None
        )
        
    # 2. Update user profile preferences
    current_prof = get_profile_by_user_id(user["id"]) or {}
    updated_profile = upsert_profile(
        user_id=user["id"],
        ptype=req.type or current_prof.get("type", user.get("role", "student")),
        major_domain=req.major_domain if req.major_domain is not None else current_prof.get("major_domain", "Engineering & Computing"),
        degree_level_stage=req.degree_level_stage if req.degree_level_stage is not None else current_prof.get("degree_level_stage", "Undergraduate BS"),
        gpa_funding=req.gpa_funding if req.gpa_funding is not None else current_prof.get("gpa_funding", "3.6 CGPA"),
        country_preference=req.country_preference if req.country_preference is not None else current_prof.get("country_preference", "Pakistan"),
        extra_details=req.extra_details
    )
    
    fresh_user = get_user_by_id(user["id"])
    return {
        "success": True,
        "message": "Profile details updated successfully.",
        "user": {
            "id": fresh_user["id"],
            "name": fresh_user["name"],
            "email": fresh_user["email"],
            "role": fresh_user["role"],
            "plan": fresh_user["plan"],
            "avatar_url": updated_profile.get("avatar_url") or get_avatar_url(fresh_user["id"])
        },
        "profile": updated_profile
    }
