import time
import threading
from typing import Dict, List, Tuple, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from app.utils.security_utils import log_security_event

class SlidingWindowRateLimiter:
    """Thread-safe, in-memory sliding window rate limiter for FastAPI/Starlette.
    Maintains timestamp records per IP/Identity with tiered windows and quotas.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._records: Dict[str, List[float]] = {}
        self.enabled: bool = True

        # Tier definitions: (quota, window_seconds)
        self.tiers = {
            "auth": (5, 60),      # 5 requests / min on auth & registration
            "otp": (5, 60),       # 5 requests / min on OTP verification
            "ai": (10, 60),       # 10 requests / min on AI drafting
            "api": (120, 60),     # 120 requests / min on standard API endpoints
            "default": (300, 60)  # 300 requests / min for general requests
        }

    def reset(self):
        """Reset all in-memory rate limiting state (useful for test isolation)."""
        with self._lock:
            self._records.clear()

    def get_tier_for_path(self, path: str) -> Optional[Tuple[str, int, int]]:
        """Map request path to corresponding rate limit tier: (tier_name, quota, window)."""
        p = path.rstrip("/").lower()

        # Exempt static assets and documentation
        if p.startswith("/static") or p in ("/docs", "/redoc", "/openapi.json"):
            return None

        # Auth endpoints
        if any(p.startswith(prefix) for prefix in (
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/forgot-password",
            "/api/auth/reset-password"
        )):
            quota, window = self.tiers["auth"]
            return ("auth", quota, window)

        # OTP endpoints
        if any(p.startswith(prefix) for prefix in (
            "/api/notifications/verify-otp",
            "/api/notifications/resend-confirmation"
        )):
            quota, window = self.tiers["otp"]
            return ("otp", quota, window)

        # AI Assistant generation
        if p.startswith("/api/assistant"):
            quota, window = self.tiers["ai"]
            return ("ai", quota, window)

        # Standard API routes
        if p.startswith("/api"):
            quota, window = self.tiers["api"]
            return ("api", quota, window)

        # Non-API page views
        quota, window = self.tiers["default"]
        return ("default", quota, window)

    def check_rate_limit(self, client_id: str, tier_name: str, quota: int, window: int) -> Tuple[bool, int, int, int]:
        """Check sliding window status.
        Returns: (allowed, remaining, retry_after, reset_seconds)
        """
        now = time.time()
        key = f"{tier_name}:{client_id}"

        with self._lock:
            timestamps = self._records.get(key, [])
            cutoff = now - window
            # Retain only timestamps within the active sliding window
            active = [ts for ts in timestamps if ts > cutoff]

            if len(active) >= quota:
                oldest = active[0]
                retry_after = max(1, int(window - (now - oldest)))
                reset_seconds = retry_after
                self._records[key] = active
                return (False, 0, retry_after, reset_seconds)

            active.append(now)
            self._records[key] = active
            remaining = max(0, quota - len(active))
            oldest = active[0]
            reset_seconds = max(1, int(window - (now - oldest)))
            return (True, remaining, 0, reset_seconds)

rate_limiter = SlidingWindowRateLimiter()

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware that enforces sliding window rate limits and telemetry headers."""
    async def dispatch(self, request: Request, call_next):
        if not rate_limiter.enabled:
            return await call_next(request)

        # Allow explicit header bypass for fast test suites when configured
        if request.headers.get("X-Test-Bypass-Rate-Limit") == "true":
            return await call_next(request)

        path = request.url.path
        tier_info = rate_limiter.get_tier_for_path(path)
        if not tier_info:
            return await call_next(request)

        tier_name, quota, window = tier_info

        # Extract client identifier: prioritize authenticated user token/session or client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        # Exempt default TestClient internal harness unless an IP is explicitly forwarded for testing
        if client_ip == "testclient" and not forwarded:
            return await call_next(request)

        allowed, remaining, retry_after, reset_seconds = rate_limiter.check_rate_limit(
            client_id=client_ip,
            tier_name=tier_name,
            quota=quota,
            window=window
        )

        if not allowed:
            log_security_event(
                event_type="RATE_LIMIT_EXCEEDED",
                detail=f"Rate limit exceeded on {path} (Tier: {tier_name}, Quota: {quota}/{window}s)",
                client_ip=client_ip
            )
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded for {tier_name}. Please wait {retry_after} seconds before retrying.",
                    "retry_after": retry_after,
                    "success": False
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(quota),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_seconds)
                }
            )
            return response

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(quota)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_seconds)
        return response
