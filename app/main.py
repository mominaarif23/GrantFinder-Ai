import os
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.db import init_db, get_user_by_email, create_user
from app.auth import hash_password
from app.routers import auth_routes, opportunity_routes, assistant_routes, dashboard_routes

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite tables and seed curated opportunities & admin account
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered discovery platform for scholarships and startup grants combining curated databases and live web search.",
    version="1.0.0",
    lifespan=lifespan
)

from fastapi.middleware.cors import CORSMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.utils.security_utils import log_security_event

# 1. Rate Limiting Middleware (Sliding Window)
app.add_middleware(RateLimiterMiddleware)

# 2. CORS configuration for cross-origin client integration & OPTIONS preflight
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Content Security Policy (CSP) & Institutional HTTP Security Headers
CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: https: blob:; "
    "connect-src 'self' https:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)

@app.middleware("http")
async def add_security_headers_and_csrf_guard(request: Request, call_next):
    # CSRF Origin validation on state-changing requests
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        origin = request.headers.get("origin")
        if origin:
            from urllib.parse import urlparse
            origin_parsed = urlparse(origin)
            origin_host = origin_parsed.netloc.lower()
            request_host = (request.headers.get("host") or "").lower()
            # If origin is provided and doesn't match host (or localhost/testing aliases), block request
            allowed_hosts = {request_host, "testserver", "localhost", "127.0.0.1"}
            origin_base = origin_host.split(":")[0]
            req_base = request_host.split(":")[0]
            if origin_base not in allowed_hosts and origin_base != req_base:
                log_security_event(
                    event_type="CSRF_BLOCKED",
                    detail=f"Forbidden cross-origin state change attempt from {origin} to {request.url.path}",
                    client_ip=request.client.host if request.client else "unknown"
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-Site Request Forgery (CSRF) origin verification failed.", "success": False}
                )

    response = await call_next(request)
    response.headers["Content-Security-Policy"] = CSP_POLICY
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return response

# Static files and templates
static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Register routers
app.include_router(auth_routes.router)
app.include_router(opportunity_routes.router)
app.include_router(assistant_routes.router)
app.include_router(dashboard_routes.router)

from app.auth import get_current_user
from fastapi import Depends
from typing import Dict, Any

@app.post("/api/user/upgrade")
def user_upgrade_route(user: Dict[str, Any] = Depends(get_current_user)):
    return opportunity_routes.mock_upgrade_plan(user)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        first_err = errors[0]
        field = first_err.get("loc", ["field"])[-1]
        msg = first_err.get("msg", "Invalid input value.")
        if msg.startswith("Value error, "):
            msg = msg.replace("Value error, ", "")
        field_name = str(field).replace("_", " ").title()
        user_msg = f"{field_name}: {msg}"
    else:
        user_msg = "Invalid request parameters provided."
    return JSONResponse(
        status_code=422,
        content={"detail": user_msg, "success": False, "errors": errors}
    )

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return templates.TemplateResponse(
        request=request,
        name="base.html",
        context={
            "user": None,
            "error_title": "404 - Page Not Found",
            "error_message": "The requested resource could not be found."
        },
        status_code=404
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
