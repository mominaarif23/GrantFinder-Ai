from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Response, Request, Depends, UploadFile, File, BackgroundTasks
from typing import Dict, Any, Optional
import os
from app.models import (
    UserRegisterRequest, UserLoginRequest, ProfileUpdateRequest, 
    ProfileDetailsUpdateRequest, UserResponse, OnboardingProfileRequest,
    VerifyOtpRequest, ResendOtpRequest, ForgotPasswordRequest, ResetPasswordRequest
)
from app.db import (
    create_user, get_user_by_email, get_user_by_id, upsert_profile, 
    get_profile_by_user_id, upload_avatar, delete_avatar, get_avatar_url,
    update_user_details, set_email_subscription, is_user_verified, set_user_verified,
    generate_registration_otp, verify_registration_otp, resend_registration_otp,
    get_latest_registration_otp, generate_password_reset, verify_and_consume_password_reset,
    update_user_password
)
from app.auth import (
    hash_password, verify_password, create_access_token, get_current_user, 
    require_verified_user, is_user_email_verified, get_current_user_optional
)
from app.services.notification_service import (
    send_optin_confirmation_email, send_registration_otp_email, send_password_reset_email
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, response: Response, background_tasks: BackgroundTasks):
    existing = get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")
    
    pwd_hash = hash_password(req.password)
    # New accounts are created in a pending verification state (email_verified=False)
    user = create_user(name=req.name, email=req.email, password_hash=pwd_hash, role=req.role, plan="free", email_verified=False)
    
    # Auto-login: issue JWT cookie for the verification session
    token = create_access_token({"sub": user["id"], "role": user["role"], "plan": user["plan"]})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax"
    )

    # Immediately generate and send a 6-digit OTP code to the entered email via Gmail SMTP
    otp_code = generate_registration_otp(user["id"], user["email"])
    try:
        background_tasks.add_task(
            send_registration_otp_email,
            recipient_email=user["email"],
            user_name=user.get("name", "Applicant"),
            otp_code=otp_code
        )
    except Exception:
        pass
    
    return {
        "success": True,
        "email_verified": False,
        "redirect": "/verify-otp",
        "message": "Registration successful. A 6-digit verification code has been dispatched to your email.",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "plan": user["plan"],
            "email_verified": False
        },
        "token": token,
        "otp": otp_code
    }

@router.post("/login")
def login(req: UserLoginRequest, response: Response, background_tasks: BackgroundTasks):
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

    verified = is_user_verified(user["id"]) or is_user_verified(user["email"])
    if not verified:
        otp_code = get_latest_registration_otp(user["id"]) or get_latest_registration_otp(user["email"])
        if not otp_code:
            otp_code = generate_registration_otp(user["id"], user["email"])
            try:
                background_tasks.add_task(
                    send_registration_otp_email,
                    recipient_email=user["email"],
                    user_name=user.get("name", "Applicant"),
                    otp_code=otp_code
                )
            except Exception:
                pass
        return {
            "success": True,
            "email_verified": False,
            "redirect": "/verify-otp",
            "message": "Account email is pending verification. Redirecting to verification page.",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "plan": user["plan"],
                "email_verified": False
            },
            "token": token,
            "otp": otp_code
        }
    
    return {
        "success": True,
        "email_verified": True,
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "plan": user["plan"],
            "email_verified": True
        },
        "token": token
    }

@router.post("/verify-registration-otp")
async def verify_registration_otp_endpoint(req: VerifyOtpRequest, request: Request):
    user = get_current_user_optional(request)
    identifier = (user and user.get("id")) or (req.email and str(req.email).strip().lower())
    if not identifier:
        raise HTTPException(status_code=400, detail="Account identifier or active session required.")

    result = verify_registration_otp(identifier, req.code)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Invalid verification code."))

    user_id = result.get("user_id") or (user and user.get("id"))
    if user_id:
        set_user_verified(user_id, True)

    return {
        "success": True,
        "message": "Email verified successfully! Your account is now fully active.",
        "redirect": "/onboarding"
    }

@router.post("/resend-registration-otp")
async def resend_registration_otp_endpoint(req: ResendOtpRequest, request: Request, background_tasks: BackgroundTasks):
    user = get_current_user_optional(request)
    identifier = (user and user.get("id")) or (req.email and str(req.email).strip().lower())
    if not identifier:
        raise HTTPException(status_code=400, detail="Account identifier or active session required.")

    result = resend_registration_otp(identifier, cooldown_seconds=60)
    if not result.get("success"):
        raise HTTPException(status_code=429, detail=result.get("message", "Please wait before requesting another code."))

    email = result.get("email") or (user and user.get("email")) or (req.email and str(req.email).strip().lower())
    user_name = (user and user.get("name")) or "Applicant"
    new_otp = result.get("otp")

    if email and new_otp:
        try:
            background_tasks.add_task(
                send_registration_otp_email,
                recipient_email=email,
                user_name=user_name,
                otp_code=new_otp
            )
        except Exception:
            pass

    return {
        "success": True,
        "message": "A new 6-digit verification code has been sent to your email.",
        "otp": new_otp
    }

@router.post("/forgot-password")
async def forgot_password_endpoint(req: ForgotPasswordRequest, request: Request, background_tasks: BackgroundTasks):
    email = str(req.email).strip().lower()
    res = generate_password_reset(email)
    base_url = str(request.base_url).rstrip("/")

    if res.get("found"):
        user = res.get("user") or {}
        user_name = user.get("name", "Applicant")
        try:
            background_tasks.add_task(
                send_password_reset_email,
                recipient_email=email,
                user_name=user_name,
                reset_code=res["code"],
                reset_token=res["token"],
                base_url=base_url
            )
        except Exception:
            pass

    # Security best practice: Never confirm or deny account existence
    return {
        "success": True,
        "message": "If this email exists in our system, password reset instructions and a verification code have been dispatched."
    }

@router.post("/reset-password")
async def reset_password_endpoint(req: ResetPasswordRequest):
    email = str(req.email).strip().lower()
    res = verify_and_consume_password_reset(email, req.code)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message", "Invalid or expired password reset code."))

    user_id = res.get("user_id")
    if not user_id:
        user = get_user_by_email(email)
        user_id = user["id"] if user else None

    if not user_id:
        raise HTTPException(status_code=400, detail="Account could not be found.")

    new_hash = hash_password(req.new_password)
    update_user_password(user_id, new_hash)

    return {
        "success": True,
        "message": "Password reset successfully. You may now sign in with your new credentials.",
        "redirect": "/login"
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
def update_profile(req: ProfileUpdateRequest, user: Dict[str, Any] = Depends(require_verified_user)):
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
    user: Dict[str, Any] = Depends(require_verified_user)
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
def delete_user_avatar(user: Dict[str, Any] = Depends(require_verified_user)):
    delete_avatar(user["id"])
    upsert_profile(user_id=user["id"], avatar_url="")
    return {
        "success": True,
        "message": "Profile picture removed successfully."
    }

@router.post("/profile/onboarding")
def complete_profile_onboarding(
    req: OnboardingProfileRequest,
    user: Dict[str, Any] = Depends(require_verified_user)
):
    """Complete multi-step onboarding setup in a single atomic transaction."""
    # 1. Update user name and role if provided
    update_user_details(
        user_id=user["id"],
        name=req.name,
        role=req.role
    )

    # 2. Update email notification subscription if user selected email
    if req.notification_preference == "email":
        set_email_subscription(user["id"], True)

    # 3. Formulate profile record and metadata
    role_choice = req.role if req.role in ("student", "founder") else user.get("role", "student")
    profile_type = "academic" if role_choice == "student" else "startup"
    
    extra_details = {
        "onboarding_completed": True,
        "notification_preference": req.notification_preference,
        "semester_or_funding": req.semester_or_funding
    }
    
    upserted_profile = upsert_profile(
        user_id=user["id"],
        ptype=profile_type,
        major_domain=req.major_domain,
        degree_level_stage=req.degree_level_stage,
        gpa_funding=req.semester_or_funding or "",
        country_preference=req.country_preference,
        extra_details=extra_details,
        avatar_url=req.avatar_url
    )

    # Determine role-specific dashboard redirect
    target_dashboard = "/dashboard/founder" if role_choice == "founder" else "/dashboard/student"

    return {
        "success": True,
        "message": "Profile setup completed successfully.",
        "redirect_url": target_dashboard,
        "profile": upserted_profile
    }

@router.post("/profile/details")
def update_profile_details(
    req: ProfileDetailsUpdateRequest,
    user: Dict[str, Any] = Depends(require_verified_user)
):
    # 1. Update user credentials (name / email / role) if changed
    if req.name or req.email or req.role:
        update_user_details(
            user_id=user["id"],
            name=req.name,
            email=str(req.email) if req.email else None,
            role=req.role
        )

    # 2. Update notification subscription preference if provided
    if req.notification_preference is not None:
        if req.notification_preference == "email":
            set_email_subscription(user["id"], True)
        elif req.notification_preference == "in_app":
            set_email_subscription(user["id"], False)
        
    # 3. Build extra_details dictionary with optional matching fields
    current_prof = get_profile_by_user_id(user["id"]) or {}
    extra_dict = dict(current_prof.get("extra_details") or {})
    if req.extra_details:
        extra_dict.update(req.extra_details)
        
    if req.university is not None:
        extra_dict["university"] = req.university.strip()
    if req.cgpa is not None:
        extra_dict["cgpa"] = req.cgpa.strip()
    if req.city is not None:
        extra_dict["city"] = req.city.strip()
    if req.grad_year is not None:
        extra_dict["grad_year"] = req.grad_year.strip()
    if req.test_scores is not None:
        extra_dict["test_scores"] = req.test_scores.strip()
    if req.financial_need is not None:
        extra_dict["financial_need"] = req.financial_need.strip()
    if req.semester is not None:
        extra_dict["semester"] = req.semester.strip()
    if req.notification_preference is not None:
        extra_dict["notification_preference"] = req.notification_preference

    # 4. Update user profile preferences
    role_to_use = req.role or user.get("role", "student")
    type_to_use = req.type or current_prof.get("type", "academic" if role_to_use == "student" else "founder")
    semester_val = req.semester if req.semester is not None else (req.gpa_funding if req.gpa_funding is not None else current_prof.get("gpa_funding", ""))
    
    updated_profile = upsert_profile(
        user_id=user["id"],
        ptype=type_to_use,
        major_domain=req.major_domain if req.major_domain is not None else current_prof.get("major_domain", "Engineering & Computing"),
        degree_level_stage=req.degree_level_stage if req.degree_level_stage is not None else current_prof.get("degree_level_stage", "Undergraduate BS"),
        gpa_funding=semester_val,
        country_preference=req.country_preference if req.country_preference is not None else current_prof.get("country_preference", "Pakistan"),
        extra_details=extra_dict,
        avatar_url=req.avatar_url if req.avatar_url is not None else current_prof.get("avatar_url")
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
