import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
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

# Enable CORS for cross-origin client integration & OPTIONS preflight (BUG-008)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enforce Institutional HTTP Security Headers (BUG-006)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
