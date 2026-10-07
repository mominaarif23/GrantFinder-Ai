from datetime import datetime, timezone
import os
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
from app.auth import get_current_user_optional, get_current_user, require_admin, is_user_email_verified
from app.db import (
    get_profile_by_user_id, get_user_notifications, get_saved_opportunities,
    get_platform_analytics, list_curated_opportunities, list_all_users,
    add_curated_opportunity, delete_curated_opportunity, mark_notification_read,
    get_avatar_url, set_email_subscription, is_email_subscribed,
    verify_subscription_token, get_user_by_id, calculate_profile_completion_pct,
    verify_email_otp, get_latest_registration_otp, generate_registration_otp
)
from app.models import CuratedOpportunityCreate
from app.services.notification_service import send_optin_confirmation_email
from app.services.supabase_service import supabase_service

templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)

router = APIRouter(tags=["Frontend Views & Dashboards"])

@router.get("/", response_class=HTMLResponse)
def index_view(request: Request):
    user = get_current_user_optional(request)
    return templates.TemplateResponse(request=request, name="index.html", context={"user": user})

@router.get("/login", response_class=HTMLResponse)
def login_view(request: Request):
    user = get_current_user_optional(request)
    if user:
        if not is_user_email_verified(user):
            return RedirectResponse(url="/verify-otp", status_code=302)
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html", context={"user": None})

@router.get("/register", response_class=HTMLResponse)
def register_view(request: Request):
    user = get_current_user_optional(request)
    if user:
        if not is_user_email_verified(user):
            return RedirectResponse(url="/verify-otp", status_code=302)
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="register.html", context={"user": None})

@router.get("/verify-otp", response_class=HTMLResponse)
def verify_otp_view(request: Request):
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url="/login?next=/verify-otp", status_code=302)
    if is_user_email_verified(user):
        return RedirectResponse(url="/dashboard", status_code=302)
    
    active_otp = get_latest_registration_otp(user["id"]) or get_latest_registration_otp(user["email"])
    if not active_otp:
        active_otp = generate_registration_otp(user["id"], user["email"])

    return templates.TemplateResponse(request=request, name="verify_otp.html", context={
        "user": user,
        "active_otp": active_otp
    })

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_view(request: Request):
    user = get_current_user_optional(request)
    if user and is_user_email_verified(user):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="forgot_password.html", context={"user": user})

@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_view(request: Request):
    token = request.query_params.get("token", "")
    email = request.query_params.get("email", "")
    return templates.TemplateResponse(request=request, name="reset_password.html", context={
        "user": None,
        "token": token,
        "email": email
    })

@router.get("/onboarding", response_class=HTMLResponse)
def onboarding_view(request: Request):
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url="/login?next=/onboarding", status_code=302)
    if not is_user_email_verified(user):
        return RedirectResponse(url="/verify-otp", status_code=302)
    if user.get("role") == "admin":
        return RedirectResponse(url="/admin", status_code=302)
    
    profile = get_profile_by_user_id(user["id"])
    avatar = (profile and profile.get("avatar_url")) or get_avatar_url(user["id"])
    user["avatar_url"] = avatar
    
    return templates.TemplateResponse(request=request, name="onboarding.html", context={
        "user": user,
        "profile": profile,
        "avatar_url": avatar
    })

@router.get("/dashboard")
def dashboard_redirect(request: Request):
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not is_user_email_verified(user):
        return RedirectResponse(url="/verify-otp", status_code=302)
    if user.get("role") == "admin":
        return RedirectResponse(url="/admin", status_code=302)
        
    profile = get_profile_by_user_id(user["id"])
    if not profile:
        return RedirectResponse(url="/onboarding", status_code=302)
        
    if user.get("role") == "founder":
        return RedirectResponse(url="/dashboard/founder", status_code=302)
    return RedirectResponse(url="/dashboard/student", status_code=302)

@router.get("/dashboard/student", response_class=HTMLResponse)
def student_dashboard_view(request: Request):
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not is_user_email_verified(user):
        return RedirectResponse(url="/verify-otp", status_code=302)
    
    profile = get_profile_by_user_id(user["id"])
    if not profile:
        return RedirectResponse(url="/onboarding", status_code=302)
        
    notifications = get_user_notifications(user["id"])
    saved = get_saved_opportunities(user["id"])
    avatar = (profile and profile.get("avatar_url")) or get_avatar_url(user["id"])
    user["avatar_url"] = avatar
    completion_pct = profile.get("completion_pct") or calculate_profile_completion_pct(user, profile)
    
    return templates.TemplateResponse(request=request, name="student_dashboard.html", context={
        "user": user,
        "profile": profile,
        "avatar_url": avatar,
        "completion_pct": completion_pct,
        "notifications": notifications,
        "saved": saved
    })

@router.get("/dashboard/founder", response_class=HTMLResponse)
def founder_dashboard_view(request: Request):
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if not is_user_email_verified(user):
        return RedirectResponse(url="/verify-otp", status_code=302)
    
    profile = get_profile_by_user_id(user["id"])
    if not profile:
        return RedirectResponse(url="/onboarding", status_code=302)
        
    notifications = get_user_notifications(user["id"])
    saved = get_saved_opportunities(user["id"])
    avatar = (profile and profile.get("avatar_url")) or get_avatar_url(user["id"])
    user["avatar_url"] = avatar
    completion_pct = profile.get("completion_pct") or calculate_profile_completion_pct(user, profile)
    
    return templates.TemplateResponse(request=request, name="founder_dashboard.html", context={
        "user": user,
        "profile": profile,
        "avatar_url": avatar,
        "completion_pct": completion_pct,
        "notifications": notifications,
        "saved": saved
    })

@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard_view(request: Request):
    user = get_current_user_optional(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=admin_required", status_code=302)
    if not is_user_email_verified(user):
        return RedirectResponse(url="/verify-otp", status_code=302)
    
    avatar = get_avatar_url(user["id"])
    user["avatar_url"] = avatar
    analytics = get_platform_analytics()
    curated_items = list_curated_opportunities()
    users_list = list_all_users()
    
    return templates.TemplateResponse(request=request, name="admin_dashboard.html", context={
        "user": user,
        "avatar_url": avatar,
        "analytics": analytics,
        "curated": curated_items,
        "users": users_list
    })

# ==============================================================================
# Admin & Notification API Endpoints
# ==============================================================================

@router.post("/api/admin/curated")
def create_curated_entry(req: CuratedOpportunityCreate, admin_user: Dict[str, Any] = Depends(require_admin)):
    data = req.model_dump()
    created = add_curated_opportunity(data)
    return {"success": True, "created": created}

@router.delete("/api/admin/curated/{opp_id}")
def remove_curated_entry(opp_id: str, admin_user: Dict[str, Any] = Depends(require_admin)):
    delete_curated_opportunity(opp_id)
    return {"success": True, "message": "Curated opportunity deleted"}

@router.post("/api/notifications/read/{nid}")
def mark_read(nid: str, user: Dict[str, Any] = Depends(get_current_user)):
    mark_notification_read(nid, user["id"])
    return {"success": True}

# ==============================================================================
# Profile View & Double Opt-In Email Subscription Endpoints
# ==============================================================================

@router.get("/profile", response_class=HTMLResponse)
def profile_view(request: Request):
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url="/login?next=/profile", status_code=302)
    if not is_user_email_verified(user):
        return RedirectResponse(url="/verify-otp", status_code=302)
    
    profile = get_profile_by_user_id(user["id"])
    avatar = (profile and profile.get("avatar_url")) or get_avatar_url(user["id"])
    user["avatar_url"] = avatar
    email_sub = is_email_subscribed(user["id"])
    notifications = get_user_notifications(user["id"])
    completion_pct = (profile and profile.get("completion_pct")) or calculate_profile_completion_pct(user, profile)
    
    active_otp = None
    if not email_sub:
        active_otp = supabase_service.get_latest_otp(user["id"]) or supabase_service.get_latest_otp(user["email"])
        if not active_otp:
            active_otp = supabase_service.generate_email_otp(user["id"], user["email"])

    return templates.TemplateResponse(request=request, name="profile.html", context={
        "user": user,
        "profile": profile,
        "avatar_url": avatar,
        "completion_pct": completion_pct,
        "email_subscribed": email_sub,
        "active_otp": active_otp,
        "notifications": notifications,
        "active_tab": "profile",
        "confirmed": request.query_params.get("confirmed") == "true",
        "unsubscribed": request.query_params.get("unsubscribed") == "true"
    })

@router.get("/api/notifications/confirm-email", response_class=HTMLResponse)
def confirm_email_subscription(request: Request, token: str):
    payload = verify_subscription_token(token)
    if not payload or payload.get("action") != "confirm":
        return HTMLResponse(
            content="""
            <html><head><title>Invalid Link</title><link rel="stylesheet" href="/static/css/styles.css"></head>
            <body class="bg-slate-950 text-white min-h-screen flex items-center justify-center p-6">
                <div class="max-w-md w-full bg-slate-900 border border-red-500/30 rounded-2xl p-8 text-center">
                    <h2 class="text-xl font-bold text-red-400 mb-3">Verification Link Expired or Invalid</h2>
                    <p class="text-slate-400 text-sm mb-6">This verification token could not be verified. Please log into your profile to request a new link.</p>
                    <a href="/login" class="inline-block px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition">Go to Sign In</a>
                </div>
            </body></html>
            """,
            status_code=400
        )
    
    user_id = payload.get("sub")
    set_email_subscription(user_id, True)
    
    user = get_current_user_optional(request)
    if user and user.get("id") == user_id:
        return RedirectResponse(url="/profile?confirmed=true", status_code=302)
        
    return HTMLResponse(
        content="""
        <html><head><title>Notifications Confirmed</title><link rel="stylesheet" href="/static/css/styles.css"></head>
        <body class="bg-slate-950 text-white min-h-screen flex items-center justify-center p-6">
            <div class="max-w-md w-full bg-slate-900 border border-emerald-500/30 rounded-2xl p-8 text-center">
                <div class="w-12 h-12 bg-emerald-500/10 border border-emerald-500/30 rounded-full flex items-center justify-center mx-auto mb-4 text-emerald-400 font-bold text-lg">OK</div>
                <h2 class="text-xl font-bold text-white mb-2">Email Notifications Confirmed</h2>
                <p class="text-slate-400 text-sm mb-6">Your double opt-in verification is complete. You will now receive high-match scholarship alerts and grant deadline reminders directly in your inbox.</p>
                <a href="/login" class="inline-block px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold transition">Sign In to Dashboard</a>
            </div>
        </body></html>
        """,
        status_code=200
    )

@router.get("/api/notifications/unsubscribe", response_class=HTMLResponse)
def unsubscribe_email(request: Request, token: str):
    payload = verify_subscription_token(token)
    if not payload:
        return HTMLResponse(
            content="""
            <html><head><title>Invalid Link</title><link rel="stylesheet" href="/static/css/styles.css"></head>
            <body class="bg-slate-950 text-white min-h-screen flex items-center justify-center p-6">
                <div class="max-w-md w-full bg-slate-900 border border-red-500/30 rounded-2xl p-8 text-center">
                    <h2 class="text-xl font-bold text-red-400 mb-3">Invalid Unsubscribe Link</h2>
                    <p class="text-slate-400 text-sm mb-6">The unsubscribe token is expired or invalid.</p>
                    <a href="/login" class="inline-block px-5 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold">Go to Login</a>
                </div>
            </body></html>
            """,
            status_code=400
        )
    
    user_id = payload.get("sub")
    set_email_subscription(user_id, False)
    
    return HTMLResponse(
        content="""
        <html><head><title>Unsubscribed</title><link rel="stylesheet" href="/static/css/styles.css"></head>
        <body class="bg-slate-950 text-white min-h-screen flex items-center justify-center p-6">
            <div class="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-8 text-center">
                <h2 class="text-xl font-bold text-white mb-2">Unsubscribed Successfully</h2>
                <p class="text-slate-400 text-sm mb-6">You have been unsubscribed from automated email notifications. You can re-enable alerts anytime from your profile settings.</p>
                <a href="/profile" class="inline-block px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-sm font-semibold transition">Back to Profile</a>
            </div>
        </body></html>
        """,
        status_code=200
    )

@router.post("/api/notifications/resend-confirmation")
def resend_confirmation(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    base_url = str(request.base_url).rstrip("/")
    dispatch_res = send_optin_confirmation_email(
        user_id=user["id"],
        recipient_email=user["email"],
        user_name=user.get("name", "Applicant"),
        base_url=base_url
    )
    active_otp = supabase_service.get_latest_otp(user["id"]) or supabase_service.get_latest_otp(user["email"])
    if not active_otp and isinstance(dispatch_res, dict):
        active_otp = dispatch_res.get("otp", "")
    smtp_ok = dispatch_res.get("smtp_delivered", True) if isinstance(dispatch_res, dict) else True

    msg = f"Confirmation email and verification code {active_otp} dispatched. Please check your inbox or notification bell."
    return {
        "success": True,
        "message": msg,
        "otp": active_otp,
        "smtp_delivered": smtp_ok
    }

@router.post("/api/notifications/verify-otp")
async def verify_otp_endpoint(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
        
    otp_code = str(data.get("otp", "")).strip()
    user = get_current_user_optional(request)
    identifier = (user and user.get("id")) or str(data.get("email", "")).strip()

    if not otp_code or not identifier:
        raise HTTPException(status_code=400, detail="Please provide both a valid 6-digit OTP code and account identifier.")

    verified_user_id = verify_email_otp(identifier, otp_code)
    if not verified_user_id and user and user.get("email"):
        verified_user_id = verify_email_otp(user["email"], otp_code)

    if not verified_user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired 6-digit verification code. Please check your code or request a new one.")

    return {
        "success": True,
        "message": "Email notifications confirmed and verified successfully!",
        "user_id": verified_user_id
    }

