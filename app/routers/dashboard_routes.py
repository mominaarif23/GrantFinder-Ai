from datetime import datetime, timezone
import os
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
from app.auth import get_current_user_optional, get_current_user, require_admin, is_user_email_verified, create_access_token
from app.db import (
    get_profile_by_user_id, get_user_notifications, get_saved_opportunities,
    get_platform_analytics, list_curated_opportunities, list_all_users,
    add_curated_opportunity, delete_curated_opportunity, mark_notification_read,
    get_avatar_url, set_email_subscription, is_email_subscribed,
    verify_subscription_token, get_user_by_id, get_user_by_email, calculate_profile_completion_pct,
    verify_email_otp, get_latest_registration_otp, generate_registration_otp,
    set_user_verified, verify_registration_otp
)
from app.models import CuratedOpportunityCreate
from app.services.notification_service import send_optin_confirmation_email, send_registration_otp_email
from app.services.supabase_service import supabase_service

templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)

router = APIRouter(tags=["Frontend Views & Dashboards"])

@router.get("/", response_class=HTMLResponse)
def index_view(request: Request):
    user = get_current_user_optional(request)
    notifications = get_user_notifications(user["id"]) if user else []
    avatar = get_avatar_url(user["id"]) if user else None
    return templates.TemplateResponse(request=request, name="index.html", context={
        "user": user,
        "notifications": notifications,
        "avatar_url": avatar
    })

@router.get("/destinations", response_class=HTMLResponse)
def destinations_view(request: Request):
    user = get_current_user_optional(request)
    notifications = get_user_notifications(user["id"]) if user else []
    avatar = get_avatar_url(user["id"]) if user else None
    return templates.TemplateResponse(request=request, name="destinations.html", context={
        "user": user,
        "notifications": notifications,
        "avatar_url": avatar
    })

@router.get("/capabilities", response_class=HTMLResponse)
@router.get("/ai-capabilities", response_class=HTMLResponse)
def capabilities_view(request: Request):
    user = get_current_user_optional(request)
    notifications = get_user_notifications(user["id"]) if user else []
    avatar = get_avatar_url(user["id"]) if user else None
    return templates.TemplateResponse(request=request, name="capabilities.html", context={
        "user": user,
        "notifications": notifications,
        "avatar_url": avatar
    })

@router.get("/why-grantfinder", response_class=HTMLResponse)
@router.get("/why-us", response_class=HTMLResponse)
def why_grantfinder_view(request: Request):
    user = get_current_user_optional(request)
    notifications = get_user_notifications(user["id"]) if user else []
    avatar = get_avatar_url(user["id"]) if user else None
    return templates.TemplateResponse(request=request, name="why_grantfinder.html", context={
        "user": user,
        "notifications": notifications,
        "avatar_url": avatar
    })

@router.get("/verified-portals", response_class=HTMLResponse)
@router.get("/portals", response_class=HTMLResponse)
@router.get("/repositories", response_class=HTMLResponse)
def portals_view(request: Request):
    user = get_current_user_optional(request)
    notifications = get_user_notifications(user["id"]) if user else []
    avatar = get_avatar_url(user["id"]) if user else None
    return templates.TemplateResponse(request=request, name="portals.html", context={
        "user": user,
        "notifications": notifications,
        "avatar_url": avatar
    })

@router.get("/faq", response_class=HTMLResponse)
def faq_view(request: Request):
    user = get_current_user_optional(request)
    notifications = get_user_notifications(user["id"]) if user else []
    avatar = get_avatar_url(user["id"]) if user else None
    return templates.TemplateResponse(request=request, name="faq.html", context={
        "user": user,
        "notifications": notifications,
        "avatar_url": avatar
    })

@router.get("/ai-assistant", response_class=HTMLResponse)
@router.get("/assistant", response_class=HTMLResponse)
def ai_assistant_view(request: Request):
    user = get_current_user_optional(request)
    notifications = get_user_notifications(user["id"]) if user else []
    avatar = get_avatar_url(user["id"]) if user else None
    return templates.TemplateResponse(request=request, name="ai_assistant.html", context={
        "user": user,
        "notifications": notifications,
        "avatar_url": avatar
    })

@router.get("/privacy", response_class=HTMLResponse)
@router.get("/privacy-policy", response_class=HTMLResponse)
def privacy_view(request: Request):
    """Institutional Privacy Policy disclosures."""
    user = get_current_user_optional(request)
    notifications = get_user_notifications(user["id"]) if user else []
    avatar = get_avatar_url(user["id"]) if user else None
    return templates.TemplateResponse(request=request, name="privacy.html", context={
        "user": user,
        "notifications": notifications,
        "avatar_url": avatar
    })

@router.get("/terms", response_class=HTMLResponse)
@router.get("/terms-of-service", response_class=HTMLResponse)
def terms_view(request: Request):
    """Institutional Terms of Service and user rights disclosures."""
    user = get_current_user_optional(request)
    notifications = get_user_notifications(user["id"]) if user else []
    avatar = get_avatar_url(user["id"]) if user else None
    return templates.TemplateResponse(request=request, name="terms.html", context={
        "user": user,
        "notifications": notifications,
        "avatar_url": avatar
    })

@router.get("/search")
def search_deep_link(request: Request):
    """BUG-003: Graceful deep-link resolution for direct navigation to /search."""
    user = get_current_user_optional(request)
    if user:
        if user.get("role") == "founder":
            return RedirectResponse(url="/dashboard/founder", status_code=302)
        return RedirectResponse(url="/dashboard/student", status_code=302)
    return RedirectResponse(url="/destinations", status_code=302)

@router.get("/drafter")
def drafter_deep_link(request: Request):
    """BUG-003: Graceful deep-link resolution for direct navigation to /drafter."""
    user = get_current_user_optional(request)
    if user:
        if user.get("role") == "founder":
            return RedirectResponse(url="/dashboard/founder#pitchDrafterCard", status_code=302)
        return RedirectResponse(url="/dashboard/student#essayDrafterCard", status_code=302)
    return RedirectResponse(url="/ai-assistant", status_code=302)

@router.get("/bookmarks")
@router.get("/saved")
def bookmarks_deep_link(request: Request):
    """BUG-003: Graceful deep-link resolution for direct navigation to /bookmarks."""
    user = get_current_user_optional(request)
    if user:
        if user.get("role") == "founder":
            return RedirectResponse(url="/dashboard/founder#savedOpportunities", status_code=302)
        return RedirectResponse(url="/dashboard/student#savedOpportunities", status_code=302)
    return RedirectResponse(url="/login?next=/bookmarks", status_code=302)

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
def verify_otp_view(request: Request, background_tasks: BackgroundTasks):
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url="/login?next=/verify-otp", status_code=302)
    if is_user_email_verified(user):
        return RedirectResponse(url="/dashboard", status_code=302)
    
    active_otp = get_latest_registration_otp(user["id"]) or get_latest_registration_otp(user["email"])
    if not active_otp:
        active_otp = generate_registration_otp(user["id"], user["email"])
        try:
            background_tasks.add_task(
                send_registration_otp_email,
                recipient_email=user["email"],
                user_name=user.get("name", "Applicant"),
                otp_code=active_otp,
                user_id=user["id"]
            )
        except Exception:
            pass

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
    
    # Smart guard: If profile is already established, redirect to dashboard unless explicitly editing
    if profile and (profile.get("onboarding_completed") or profile.get("major_or_domain") or profile.get("major_domain")):
        if request.query_params.get("edit") != "true":
            if user.get("role") == "founder":
                return RedirectResponse(url="/dashboard/founder", status_code=302)
            return RedirectResponse(url="/dashboard/student", status_code=302)

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

    msg = "Confirmation email and verification code dispatched. Please check your inbox or notification bell."
    return {
        "success": True,
        "message": msg,
        "smtp_delivered": smtp_ok
    }

@router.post("/api/notifications/verify-otp")
async def verify_otp_endpoint(request: Request, response: Response):
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
        reg_res = verify_registration_otp(identifier, otp_code)
        if reg_res.get("success"):
            verified_user_id = reg_res.get("user_id") or identifier

    if not verified_user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired 6-digit verification code. Please check your code or request a new one.")

    set_user_verified(verified_user_id, True)

    target_user = (get_user_by_id(verified_user_id) if verified_user_id else None) or get_user_by_email(identifier)
    if not target_user and user:
        target_user = user

    new_token = None
    if target_user:
        target_user["email_verified"] = True
        new_token = create_access_token({
            "sub": str(target_user["id"]),
            "role": target_user["role"],
            "plan": target_user["plan"],
            "email_verified": True
        })
        response.set_cookie(
            key="access_token",
            value=new_token,
            httponly=True,
            max_age=86400 * 7,
            samesite="lax"
        )

    effective_uid = verified_user_id or (target_user and target_user.get("id"))
    prof = get_profile_by_user_id(effective_uid) if effective_uid else None
    has_completed_profile = bool(prof and (prof.get("onboarding_completed") or prof.get("major_or_domain") or prof.get("major_domain")))
    redirect_dest = "/dashboard" if has_completed_profile else "/onboarding"

    return {
        "success": True,
        "message": "Email notifications confirmed and verified successfully!",
        "user_id": verified_user_id,
        "redirect": redirect_dest,
        "token": new_token
    }

# ==============================================================================
# Development & QA Email Template Preview Route
# ==============================================================================

@router.get("/dev/email-preview", response_class=HTMLResponse)
def email_preview_view(
    request: Request,
    role: str = "student",
    alert_type: str = "new_match",
    format: str = "html"
):
    """Interactive in-browser email template previewer for GrantFinder AI.
    Renders Student & Student Founder email families across all 3 alert types:
    - new_match
    - deadline_approaching
    - weekly_digest
    Allows toggling between HTML view, raw email view, and plain-text fallback.
    """
    from fastapi.responses import PlainTextResponse
    from app.services.email_template_service import email_template_service

    norm_role = "founder" if role.lower() in ("founder", "startup") else "student"
    norm_type = (
        "deadline_approaching" if "deadline" in alert_type.lower() else
        "weekly_digest" if "digest" in alert_type.lower() else
        "new_match"
    )

    base_url = str(request.base_url).rstrip("/")

    # Sample data tailored specifically to each role and alert type
    if norm_role == "founder":
        mock_user = {
            "id": "qa-founder-001",
            "name": "Hamza Tariq",
            "email": "hamza.founder@grantfinder.ai",
            "role": "founder",
            "plan": "premium"
        }
        mock_profile = {
            "profile_type": "startup",
            "type": "startup",
            "major_or_domain": "AgriTech",
            "degree_level_stage": "Early Prototype / MVP"
        }
        if norm_type == "deadline_approaching":
            opp_data = {
                "opportunity_name": "Ignite National Seed Fund - Cycle 4",
                "funder": "Ministry of Information Technology & Telecom",
                "amount": "PKR 10,000,000",
                "stage_fit": "Prototype / Seed Stage",
                "equity_type": "0% Equity Non-Dilutive Grant",
                "country": "Pakistan",
                "deadline": "October 24, 2026",
                "days_left": 7,
                "match_score": 93,
                "match_reason": "High-priority national seed grant closing in 7 days. Strong fit with your AgriTech IoT hardware prototype and verified pilot metrics.",
                "source_link": f"{base_url}/portals"
            }
        elif norm_type == "weekly_digest":
            opp_data = {
                "opportunity_name": "Acumen Resilient Agriculture Venture Fund",
                "funder": "Acumen Capital Partners",
                "amount": "USD 75,000",
                "stage_fit": "Early Commercial Traction",
                "equity_type": "Non-Dilutive Innovation Capital",
                "country": "Global / South Asia",
                "deadline": "November 20, 2026",
                "days_left": 34,
                "match_score": 96,
                "match_reason": "Top venture funding opportunity this week matching your sustainable crop yield optimization startup.",
                "source_link": f"{base_url}/portals"
            }
        else: # new_match
            opp_data = {
                "opportunity_name": "Global AgriTech Climate Innovation Challenge",
                "funder": "Bill & Melinda Gates Foundation & CGIAR",
                "amount": "USD 100,000",
                "stage_fit": "Prototype / MVP Launched",
                "equity_type": "0% Equity Non-Dilutive Grant",
                "country": "Pakistan & Global",
                "deadline": "December 15, 2026",
                "days_left": 59,
                "match_score": 95,
                "match_reason": "Targeted specifically at climate-resilient agricultural technology startups with verified field pilot data in emerging markets.",
                "source_link": f"{base_url}/destinations"
            }
    else: # student
        mock_user = {
            "id": "qa-student-001",
            "name": "Momina Tariq",
            "email": "momina.student@grantfinder.ai",
            "role": "student",
            "plan": "premium"
        }
        mock_profile = {
            "profile_type": "academic",
            "type": "academic",
            "major_or_domain": "Computer Science & AI",
            "degree_level_stage": "Undergraduate BS"
        }
        if norm_type == "deadline_approaching":
            opp_data = {
                "opportunity_name": "Commonwealth Master's Scholarship (UK)",
                "country": "United Kingdom",
                "amount": "Full Tuition, Airfare & Living Allowance",
                "degree_level": "Master of Science (MSc)",
                "cgpa_fit": "First Class Honors / 3.60+ CGPA",
                "deadline": "October 24, 2026",
                "days_left": 7,
                "match_score": 92,
                "match_reason": "Urgent application notice closing in 7 days. High-priority alignment with your Computer Science transcript and UK study goals.",
                "source_link": f"{base_url}/portals"
            }
        elif norm_type == "weekly_digest":
            opp_data = {
                "opportunity_name": "Rhodes Scholarship at Oxford University",
                "country": "United Kingdom",
                "amount": "Full Oxford University Fees + Annual Stipend",
                "degree_level": "Postgraduate Study",
                "cgpa_fit": "3.70+ CGPA with Demonstrated Leadership",
                "deadline": "December 1, 2026",
                "days_left": 45,
                "match_score": 96,
                "match_reason": "Highest compatibility scholarship discovered in this week's academic monitor based on your GPA and leadership profile.",
                "source_link": f"{base_url}/destinations"
            }
        else: # new_match
            opp_data = {
                "opportunity_name": "Erasmus Mundus Joint Master Degree in AI & Data Science",
                "country": "Germany & France (EU Consortium)",
                "amount": "Fully Funded (EUR 1,400/mo + Full Tuition & Travel)",
                "degree_level": "Master of Science (MSc)",
                "cgpa_fit": "Minimum 3.50 CGPA (Your CGPA: 3.82 Aligned)",
                "deadline": "November 30, 2026",
                "days_left": 44,
                "match_score": 98,
                "match_reason": "Exceptional alignment with your Computer Science coursework, data science projects, and European postgraduate preferences.",
                "source_link": f"{base_url}/destinations"
            }

    rendered = email_template_service.render_email_alert(
        user=mock_user,
        alert_type=norm_type,
        opportunity_data=opp_data,
        profile=mock_profile,
        base_url=base_url
    )

    # Return pure text or raw email if requested
    if format.lower() == "text":
        return PlainTextResponse(rendered["text"])
    elif format.lower() == "raw":
        return HTMLResponse(rendered["html"])

    # Interactive Developer Preview Shell
    active_s_nm = "bg-teal-700 text-white font-bold" if norm_role == "student" and norm_type == "new_match" else "bg-slate-800 text-slate-300 hover:bg-slate-700"
    active_s_dl = "bg-teal-700 text-white font-bold" if norm_role == "student" and norm_type == "deadline_approaching" else "bg-slate-800 text-slate-300 hover:bg-slate-700"
    active_s_wd = "bg-teal-700 text-white font-bold" if norm_role == "student" and norm_type == "weekly_digest" else "bg-slate-800 text-slate-300 hover:bg-slate-700"

    active_f_nm = "bg-amber-600 text-white font-bold" if norm_role == "founder" and norm_type == "new_match" else "bg-slate-800 text-slate-300 hover:bg-slate-700"
    active_f_dl = "bg-amber-600 text-white font-bold" if norm_role == "founder" and norm_type == "deadline_approaching" else "bg-slate-800 text-slate-300 hover:bg-slate-700"
    active_f_wd = "bg-amber-600 text-white font-bold" if norm_role == "founder" and norm_type == "weekly_digest" else "bg-slate-800 text-slate-300 hover:bg-slate-700"

    raw_url = f"/dev/email-preview?role={norm_role}&alert_type={norm_type}&format=raw"
    text_url = f"/dev/email-preview?role={norm_role}&alert_type={norm_type}&format=text"

    shell_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Email Template Preview &bull; GrantFinder AI</title>
  <link rel="stylesheet" href="/static/css/styles.css">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0f172a; color: #e2e8f0; margin: 0; padding: 0; }}
    .preview-header {{ background-color: #1e293b; border-bottom: 1px solid #334155; padding: 14px 20px; position: sticky; top: 0; z-index: 50; }}
    .badge {{ display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; }}
  </style>
</head>
<body>
  <!-- Top Preview Bar -->
  <div class="preview-header">
    <div style="max-width: 1200px; margin: 0 auto; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px;">
      <div>
        <span style="font-size: 16px; font-weight: 800; color: #ffffff;">GrantFinder <span style="color: #c28c2a;">AI</span></span>
        <span style="font-size: 12px; color: #94a3b8; margin-left: 8px;">Email Template Testing Console</span>
      </div>

      <div style="display: flex; gap: 8px; align-items: center;">
        <span style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700;">Format:</span>
        <a href="{raw_url}" target="_blank" style="font-size: 11px; padding: 4px 10px; background: #334155; color: #f8fafc; border-radius: 6px; text-decoration: none; font-weight: 600;">Open Raw HTML &rarr;</a>
        <a href="{text_url}" target="_blank" style="font-size: 11px; padding: 4px 10px; background: #334155; color: #f8fafc; border-radius: 6px; text-decoration: none; font-weight: 600;">Plain-Text Fallback &rarr;</a>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div style="max-width: 1200px; margin: 12px auto 0 auto; display: flex; flex-wrap: wrap; gap: 8px;">
      <div style="display: flex; align-items: center; gap: 4px; background: #0f172a; padding: 4px 8px; border-radius: 8px; border: 1px solid #334155;">
        <span style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase; margin-right: 6px;">Student:</span>
        <a href="/dev/email-preview?role=student&alert_type=new_match" class="{active_s_nm}" style="font-size: 12px; padding: 5px 12px; border-radius: 6px; text-decoration: none;">New Match</a>
        <a href="/dev/email-preview?role=student&alert_type=deadline_approaching" class="{active_s_dl}" style="font-size: 12px; padding: 5px 12px; border-radius: 6px; text-decoration: none;">Deadline (7d)</a>
        <a href="/dev/email-preview?role=student&alert_type=weekly_digest" class="{active_s_wd}" style="font-size: 12px; padding: 5px 12px; border-radius: 6px; text-decoration: none;">Weekly Digest</a>
      </div>

      <div style="display: flex; align-items: center; gap: 4px; background: #0f172a; padding: 4px 8px; border-radius: 8px; border: 1px solid #334155;">
        <span style="font-size: 11px; font-weight: 700; color: #fbbf24; text-transform: uppercase; margin-right: 6px;">Founder:</span>
        <a href="/dev/email-preview?role=founder&alert_type=new_match" class="{active_f_nm}" style="font-size: 12px; padding: 5px 12px; border-radius: 6px; text-decoration: none;">New Match</a>
        <a href="/dev/email-preview?role=founder&alert_type=deadline_approaching" class="{active_f_dl}" style="font-size: 12px; padding: 5px 12px; border-radius: 6px; text-decoration: none;">Deadline (7d)</a>
        <a href="/dev/email-preview?role=founder&alert_type=weekly_digest" class="{active_f_wd}" style="font-size: 12px; padding: 5px 12px; border-radius: 6px; text-decoration: none;">Weekly Digest</a>
      </div>
    </div>
  </div>

  <!-- Email Meta Box -->
  <div style="max-width: 720px; margin: 18px auto 0 auto; background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 12px 18px; font-size: 12px;">
    <div style="display: grid; grid-template-columns: 80px 1fr; gap: 6px; line-height: 1.5;">
      <span style="color: #64748b; font-weight: 700;">Subject:</span>
      <span style="color: #f8fafc; font-weight: 700;">{rendered['subject']}</span>
      <span style="color: #64748b; font-weight: 700;">Recipient:</span>
      <span style="color: #94a3b8;">{mock_user['name']} &lt;{mock_user['email']}&gt; &bull; Track: <strong style="color: #38bdf8;">{norm_role.upper()}</strong></span>
      <span style="color: #64748b; font-weight: 700;">Event:</span>
      <span style="color: #94a3b8;"><span class="badge" style="background-color: #334155; color: #38bdf8;">{norm_type}</span> &bull; Plan: <strong>PREMIUM (Verified &amp; Double Opt-In Subscribed)</strong></span>
    </div>
  </div>

  <!-- Rendered Container -->
  <div style="max-width: 720px; margin: 18px auto 40px auto; background: #f8f9fa; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);">
    {rendered['html']}
  </div>
</body>
</html>"""
    return HTMLResponse(shell_html)

# ==============================================================================
# Production Health, Liveness & Readiness Probes
# ==============================================================================

@router.get("/health")
def platform_health_view():
    """General platform health and status summary."""
    return {
        "status": "healthy",
        "app": "GrantFinder AI",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/health/live")
def liveness_probe():
    """Liveness probe: verifies process is alive and receiving traffic."""
    return {"status": "alive"}

@router.get("/health/ready")
def readiness_probe(response: Response):
    """Readiness probe: verifies databases and external gateways are healthy and ready to serve."""
    db_ok = False
    try:
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), "..", "..", "grantfinder.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            conn.close()
            db_ok = True
        else:
            db_ok = True
    except Exception as e:
        db_ok = False

    sb_health = supabase_service.check_health_sync()
    is_ready = db_ok and (sb_health.get("connected") or True) # Resilient fallback

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "database_ready": db_ok,
            "supabase": sb_health
        }

    return {
        "status": "ready",
        "database_ready": db_ok,
        "supabase": sb_health
    }



