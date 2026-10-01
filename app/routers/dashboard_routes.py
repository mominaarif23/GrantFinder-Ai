import os
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
from app.auth import get_current_user_optional, get_current_user, require_admin
from app.db import (
    get_profile_by_user_id, get_user_notifications, get_saved_opportunities,
    get_platform_analytics, list_curated_opportunities, list_all_users,
    add_curated_opportunity, delete_curated_opportunity, mark_notification_read
)
from app.models import CuratedOpportunityCreate

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
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html", context={"user": None})

@router.get("/register", response_class=HTMLResponse)
def register_view(request: Request):
    user = get_current_user_optional(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="register.html", context={"user": None})

@router.get("/dashboard")
def dashboard_redirect(request: Request):
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user.get("role") == "admin":
        return RedirectResponse(url="/admin", status_code=302)
    elif user.get("role") == "founder":
        return RedirectResponse(url="/dashboard/founder", status_code=302)
    return RedirectResponse(url="/dashboard/student", status_code=302)

@router.get("/dashboard/student", response_class=HTMLResponse)
def student_dashboard_view(request: Request):
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    profile = get_profile_by_user_id(user["id"])
    notifications = get_user_notifications(user["id"])
    saved = get_saved_opportunities(user["id"])
    
    return templates.TemplateResponse(request=request, name="student_dashboard.html", context={
        "user": user,
        "profile": profile,
        "notifications": notifications,
        "saved": saved
    })

@router.get("/dashboard/founder", response_class=HTMLResponse)
def founder_dashboard_view(request: Request):
    user = get_current_user_optional(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    profile = get_profile_by_user_id(user["id"])
    notifications = get_user_notifications(user["id"])
    saved = get_saved_opportunities(user["id"])
    
    return templates.TemplateResponse(request=request, name="founder_dashboard.html", context={
        "user": user,
        "profile": profile,
        "notifications": notifications,
        "saved": saved
    })

@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard_view(request: Request):
    user = get_current_user_optional(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login?error=admin_required", status_code=302)
    
    analytics = get_platform_analytics()
    curated_items = list_curated_opportunities()
    users_list = list_all_users()
    
    return templates.TemplateResponse(request=request, name="admin_dashboard.html", context={
        "user": user,
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
