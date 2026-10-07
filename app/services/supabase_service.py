import os
import uuid
import json
import httpx
import jwt
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from app.config import settings

# In-memory runtime persistence caches for instant responsiveness and resilience
_USER_AVATARS: Dict[str, str] = {}
_USER_SUBSCRIPTIONS: Dict[str, bool] = {}
_USER_EXTRA_DETAILS: Dict[str, Dict[str, Any]] = {}
_EMAIL_OTPS: Dict[str, Dict[str, Any]] = {}
_USER_VERIFIED: Dict[str, bool] = {}
_REGISTRATION_OTPS: Dict[str, Dict[str, Any]] = {}
_PASSWORD_RESET_OTPS: Dict[str, Dict[str, Any]] = {}
_USER_PROFILES: Dict[str, Dict[str, Any]] = {}
_IN_APP_NOTIFICATIONS: Dict[str, List[Dict[str, Any]]] = {}

class SupabaseService:
    @property
    def _USER_VERIFIED(self):
        return _USER_VERIFIED

    @property
    def _REGISTRATION_OTPS(self):
        return _REGISTRATION_OTPS

    @property
    def _PASSWORD_RESET_OTPS(self):
        return _PASSWORD_RESET_OTPS

    @property
    def _EMAIL_OTPS(self):
        return _EMAIL_OTPS

    @property
    def _USER_PROFILES(self):
        return _USER_PROFILES

    @property
    def _IN_APP_NOTIFICATIONS(self):
        return _IN_APP_NOTIFICATIONS

    def __init__(self):
        self.url = settings.SUPABASE_URL.rstrip('/')
        self.key = settings.SUPABASE_KEY
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    # ==========================================================================
    # System Health & Connectivity
    # ==========================================================================

    async def check_health(self) -> Dict[str, Any]:
        """Check connection status with Supabase REST gateway asynchronously."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.url}/rest/v1/", headers=self.headers)
                return {
                    "connected": res.status_code in (200, 401, 404),
                    "status_code": res.status_code,
                    "url": self.url
                }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "url": self.url
            }

    def check_health_sync(self) -> Dict[str, Any]:
        """Check connection status with Supabase REST gateway synchronously."""
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self.url}/rest/v1/", headers=self.headers)
                return {
                    "connected": res.status_code in (200, 401, 404),
                    "status_code": res.status_code,
                    "url": self.url
                }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "url": self.url
            }

    # ==========================================================================
    # User Management (public.users)
    # ==========================================================================

    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: str = "student",
        plan: str = "free",
        email_verified: bool = True
    ) -> Dict[str, Any]:
        """Insert a newly registered user directly into Supabase public.users and SQLite."""
        user_id = str(uuid.uuid4())
        clean_email = email.strip().lower()
        payload = {
            "id": user_id,
            "name": name.strip(),
            "email": clean_email,
            "password_hash": password_hash,
            "role": role,
            "plan": plan
        }
        _USER_VERIFIED[user_id] = email_verified
        _USER_VERIFIED[clean_email] = email_verified

        # Also mirror in local SQLite database
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "grantfinder.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                now_iso = datetime.now(timezone.utc).isoformat()
                cur.execute(
                    "INSERT OR REPLACE INTO users (id, name, email, password_hash, role, plan, created_at, email_verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, name.strip(), clean_email, password_hash, role, plan, now_iso, 1 if email_verified else 0)
                )
                conn.commit()
                conn.close()
        except Exception:
            pass

        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.post(
                    f"{self.url}/rest/v1/users",
                    json=payload,
                    headers=self.headers
                )
                res.raise_for_status()
                data = res.json()
                if data and len(data) > 0:
                    ret = data[0]
                    ret["email_verified"] = email_verified
                    return ret
        except Exception:
            pass

        payload["created_at"] = datetime.now(timezone.utc).isoformat()
        payload["email_verified"] = email_verified
        return payload

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Query user record from local database or Supabase public.users by email."""
        clean_email = email.strip().lower()
        user_record = None
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "grantfinder.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("SELECT id, name, email, password_hash, role, plan, created_at, email_verified FROM users WHERE email = ?", (clean_email,))
                row = cur.fetchone()
                conn.close()
                if row:
                    user_record = {
                        "id": row[0],
                        "name": row[1],
                        "email": row[2],
                        "password_hash": row[3],
                        "role": row[4],
                        "plan": row[5],
                        "created_at": row[6],
                        "email_verified": bool(row[7]) if row[7] is not None else False
                    }
        except Exception:
            pass

        if not user_record:
            try:
                with httpx.Client(timeout=3.0) as client:
                    res = client.get(
                        f"{self.url}/rest/v1/users?email=eq.{clean_email}&select=*",
                        headers=self.headers
                    )
                    if res.status_code == 200:
                        data = res.json()
                        if data and len(data) > 0:
                            user_record = data[0]
            except Exception:
                pass

        if user_record:
            user_record["email_verified"] = self.is_user_verified(user_record["id"]) or self.is_user_verified(user_record["email"])
        return user_record

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Query user record from local database or Supabase public.users by UUID."""
        user_record = None
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "grantfinder.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("SELECT id, name, email, password_hash, role, plan, created_at, email_verified FROM users WHERE id = ?", (user_id,))
                row = cur.fetchone()
                conn.close()
                if row:
                    user_record = {
                        "id": row[0],
                        "name": row[1],
                        "email": row[2],
                        "password_hash": row[3],
                        "role": row[4],
                        "plan": row[5],
                        "created_at": row[6],
                        "email_verified": bool(row[7]) if row[7] is not None else False
                    }
        except Exception:
            pass

        if not user_record:
            try:
                with httpx.Client(timeout=3.0) as client:
                    res = client.get(
                        f"{self.url}/rest/v1/users?id=eq.{user_id}&select=*",
                        headers=self.headers
                    )
                    if res.status_code == 200:
                        data = res.json()
                        if data and len(data) > 0:
                            user_record = data[0]
            except Exception:
                pass

        if user_record:
            user_record["email_verified"] = self.is_user_verified(user_record["id"]) or self.is_user_verified(user_record["email"])
        return user_record

    def update_user_plan(self, user_id: str, new_plan: str) -> bool:
        """Update subscription plan in Supabase public.users and SQLite."""
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "grantfinder.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("UPDATE users SET plan = ? WHERE id = ?", (new_plan, user_id))
                conn.commit()
                conn.close()
        except Exception:
            pass

        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.patch(
                    f"{self.url}/rest/v1/users?id=eq.{user_id}",
                    json={"plan": new_plan},
                    headers=self.headers
                )
                return res.status_code in (200, 204)
        except Exception:
            return True

    def list_all_users(self) -> List[Dict[str, Any]]:
        """List all users ordered by creation date descending."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(
                    f"{self.url}/rest/v1/users?select=id,name,email,role,plan,created_at&order=created_at.desc",
                    headers=self.headers
                )
                if res.status_code == 200:
                    return res.json()
        except Exception:
            pass

        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "grantfinder.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("SELECT id, name, email, role, plan, created_at FROM users ORDER BY created_at DESC")
                rows = cur.fetchall()
                conn.close()
                return [
                    {"id": r[0], "name": r[1], "email": r[2], "role": r[3], "plan": r[4], "created_at": r[5]}
                    for r in rows
                ]
        except Exception:
            pass
        return []

    def update_user_details(
        self,
        user_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update user name, email, and/or role in Supabase public.users and SQLite."""
        payload = {}
        if name:
            payload["name"] = name.strip()
        if email:
            payload["email"] = email.strip().lower()
        if role:
            payload["role"] = role.strip().lower()
        if not payload:
            return self.get_user_by_id(user_id)
            
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "grantfinder.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                if name:
                    cur.execute("UPDATE users SET name = ? WHERE id = ?", (name.strip(), user_id))
                if email:
                    cur.execute("UPDATE users SET email = ? WHERE id = ?", (email.strip().lower(), user_id))
                if role:
                    cur.execute("UPDATE users SET role = ? WHERE id = ?", (role.strip().lower(), user_id))
                conn.commit()
                conn.close()
        except Exception:
            pass

        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.patch(
                    f"{self.url}/rest/v1/users?id=eq.{user_id}",
                    json=payload,
                    headers=self.headers
                )
                if res.status_code in (200, 204):
                    data = res.json() if res.text else []
                    return data[0] if data else self.get_user_by_id(user_id)
        except Exception:
            pass
        return self.get_user_by_id(user_id)

    # ==========================================================================
    # Email Double Opt-In Subscription Management
    # ==========================================================================

    def set_email_subscription(self, user_id: str, subscribed: bool) -> bool:
        """Update email subscription opt-in state for user in public.users."""
        _USER_SUBSCRIPTIONS[user_id] = subscribed
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.patch(
                    f"{self.url}/rest/v1/users?id=eq.{user_id}",
                    json={"email_subscribed": subscribed},
                    headers=self.headers
                )
                return res.status_code in (200, 204)
        except Exception:
            return True

    def is_email_subscribed(self, user_id: str) -> bool:
        """Check whether user has confirmed double opt-in for automated notifications."""
        if user_id in _USER_SUBSCRIPTIONS:
            return _USER_SUBSCRIPTIONS[user_id]

        user = self.get_user_by_id(user_id)
        if user and "email_subscribed" in user:
            val = bool(user.get("email_subscribed", False))
            _USER_SUBSCRIPTIONS[user_id] = val
            return val

        # Default is False (Unconfirmed / Double Opt-in Pending)
        _USER_SUBSCRIPTIONS[user_id] = False
        return False

    def generate_subscription_token(self, user_id: str, email: str, action: str = "confirm") -> str:
        """Generate signed cryptographic JWT token for email confirmation / unsubscription."""
        payload = {
            "sub": user_id,
            "email": email.strip().lower(),
            "action": action,
            "exp": datetime.now(timezone.utc) + timedelta(days=30)
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def verify_subscription_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify signed subscription token and extract payload."""
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except Exception:
            return None

    def generate_email_otp(self, user_id: str, email: str) -> str:
        """Generate a secure 6-digit numeric OTP code for email verification (valid for 15 minutes)."""
        code = f"{secrets.randbelow(900000) + 100000}"
        expiry = datetime.now(timezone.utc) + timedelta(minutes=15)
        clean_email = email.strip().lower()
        entry = {"otp": code, "user_id": user_id, "email": clean_email, "exp": expiry}
        _EMAIL_OTPS[user_id] = entry
        _EMAIL_OTPS[clean_email] = entry
        return code

    def verify_email_otp(self, identifier: str, code: str) -> Optional[str]:
        """Verify 6-digit OTP code by user_id or email address. Returns user_id if valid, else None."""
        key = identifier.strip().lower()
        record = _EMAIL_OTPS.get(key)
        if not record and identifier in _EMAIL_OTPS:
            record = _EMAIL_OTPS[identifier]
        if not record:
            return None

        if datetime.now(timezone.utc) > record["exp"]:
            _EMAIL_OTPS.pop(key, None)
            return None

        clean_code = "".join(ch for ch in code if ch.isdigit())
        if record["otp"] == clean_code:
            user_id = record.get("user_id") or key
            self.set_email_subscription(user_id, True)
            _EMAIL_OTPS.pop(key, None)
            return user_id
        return None

    def get_latest_otp(self, identifier: str) -> Optional[str]:
        """Return the latest active OTP code for testing and automated validation."""
        key = identifier.strip().lower()
        record = _EMAIL_OTPS.get(key) or _EMAIL_OTPS.get(identifier)
        if record and datetime.now(timezone.utc) <= record["exp"]:
            return record["otp"]
        return None

    # ==========================================================================
    # User Account Verification & Registration OTP (Strict Server-Side Enforcement)
    # ==========================================================================

    def is_user_verified(self, user_id_or_email: Optional[str]) -> bool:
        """Check whether user has completed email verification."""
        if not user_id_or_email:
            return False
        key = str(user_id_or_email).strip().lower()
        if key in _USER_VERIFIED:
            return _USER_VERIFIED[key]

        # Seeded admin and test accounts are verified by default
        if key in ("admin@grantfinder.ai", "momnaaa23@gmail.com"):
            _USER_VERIFIED[key] = True
            return True

        # Check local SQLite database if available
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "grantfinder.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("SELECT email_verified FROM users WHERE id = ? OR email = ?", (key, key))
                row = cur.fetchone()
                conn.close()
                if row is not None and row[0] is not None:
                    val = bool(row[0])
                    _USER_VERIFIED[key] = val
                    return val
        except Exception:
            pass

        return False

    def set_user_verified(self, user_id_or_email: str, verified: bool = True) -> bool:
        """Set user verification state across memory and local storage."""
        if not user_id_or_email:
            return False
        key = str(user_id_or_email).strip().lower()
        _USER_VERIFIED[key] = verified

        # Also update SQLite database
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "grantfinder.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("UPDATE users SET email_verified = ? WHERE id = ? OR email = ?", (1 if verified else 0, key, key))
                conn.commit()
                conn.close()
        except Exception:
            pass

        return True

    def generate_registration_otp(self, user_id: str, email: str) -> str:
        """Generate a secure 6-digit numeric OTP code for registration verification (valid for 10 minutes)."""
        code = f"{secrets.randbelow(900000) + 100000}"
        expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
        clean_email = email.strip().lower()
        now = datetime.now(timezone.utc)
        entry = {
            "otp": code,
            "user_id": user_id,
            "email": clean_email,
            "exp": expiry,
            "attempts": 0,
            "last_sent": now
        }
        _REGISTRATION_OTPS[user_id] = entry
        _REGISTRATION_OTPS[clean_email] = entry
        return code

    def verify_registration_otp(self, identifier: str, code: str) -> Dict[str, Any]:
        """Verify 6-digit registration OTP code with attempt limiting and expiry."""
        key = identifier.strip().lower()
        record = _REGISTRATION_OTPS.get(key)
        if not record:
            return {"success": False, "message": "No active verification code found. Please request a new code."}

        # Check maximum attempts (5 attempts limit)
        if record.get("attempts", 0) >= 5:
            return {"success": False, "message": "Maximum verification attempts exceeded. Please request a new code."}

        # Check expiration (10 minutes)
        if datetime.now(timezone.utc) > record["exp"]:
            _REGISTRATION_OTPS.pop(key, None)
            return {"success": False, "message": "Verification code has expired. Please request a new code."}

        clean_code = "".join(ch for ch in code if ch.isdigit())
        if record["otp"] == clean_code:
            user_id = record.get("user_id") or key
            self.set_user_verified(user_id, True)
            clean_email = record.get("email")
            _REGISTRATION_OTPS.pop(user_id, None)
            if clean_email:
                _REGISTRATION_OTPS.pop(clean_email, None)
            return {"success": True, "message": "Email verified successfully!", "user_id": user_id}

        # Incorrect code: increment attempts count
        record["attempts"] = record.get("attempts", 0) + 1
        remaining = max(0, 5 - record["attempts"])
        if remaining == 0:
            return {"success": False, "message": "Maximum verification attempts exceeded. Please request a new code."}
        return {"success": False, "message": f"Incorrect verification code. {remaining} attempts remaining."}

    def resend_registration_otp(self, identifier: str, cooldown_seconds: int = 60) -> Dict[str, Any]:
        """Resend registration OTP code respecting the 60-second cooldown period."""
        key = identifier.strip().lower()
        record = _REGISTRATION_OTPS.get(key)
        now = datetime.now(timezone.utc)

        if record and "last_sent" in record:
            elapsed = (now - record["last_sent"]).total_seconds()
            if elapsed < cooldown_seconds:
                remaining_wait = int(cooldown_seconds - elapsed)
                return {
                    "success": False,
                    "cooldown": True,
                    "remaining_seconds": remaining_wait,
                    "message": f"Please wait {remaining_wait} seconds before requesting another code."
                }

        user_id = (record and record.get("user_id")) or key
        email = (record and record.get("email")) or key
        if "@" in key:
            user = self.get_user_by_email(key)
            if user:
                user_id = user["id"]
        else:
            user = self.get_user_by_id(key)
            if user:
                email = user["email"]

        new_code = self.generate_registration_otp(user_id, email)
        return {
            "success": True,
            "otp": new_code,
            "email": email,
            "user_id": user_id,
            "message": "A new 6-digit verification code has been dispatched."
        }

    def get_latest_registration_otp(self, identifier: str) -> Optional[str]:
        """Return the latest active registration OTP code for testing and automated validation."""
        key = identifier.strip().lower()
        record = _REGISTRATION_OTPS.get(key)
        if record and datetime.now(timezone.utc) <= record["exp"]:
            return record["otp"]
        return None

    # ==========================================================================
    # Password Reset Management (OTP & Secure Token Flow)
    # ==========================================================================

    def generate_password_reset(self, email: str) -> Dict[str, Any]:
        """Generate a 6-digit password reset OTP and signed reset token (valid for 15 minutes)."""
        clean_email = email.strip().lower()
        user = self.get_user_by_email(clean_email)
        if not user:
            return {"found": False}

        code = f"{secrets.randbelow(900000) + 100000}"
        token = jwt.encode(
            {"sub": user["id"], "email": clean_email, "type": "password_reset", "exp": datetime.now(timezone.utc) + timedelta(minutes=15)},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        entry = {
            "code": code,
            "token": token,
            "user_id": user["id"],
            "email": clean_email,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "attempts": 0
        }
        _PASSWORD_RESET_OTPS[clean_email] = entry
        _PASSWORD_RESET_OTPS[user["id"]] = entry
        return {
            "found": True,
            "user": user,
            "code": code,
            "token": token
        }

    def verify_and_consume_password_reset(self, email: str, code_or_token: str) -> Dict[str, Any]:
        """Verify password reset code or JWT token and invalidate immediately upon verification."""
        clean_email = email.strip().lower()
        record = _PASSWORD_RESET_OTPS.get(clean_email)

        # Check by JWT token if passed
        if len(code_or_token) > 20:
            try:
                payload = jwt.decode(code_or_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                if payload.get("type") == "password_reset" and payload.get("email") == clean_email:
                    _PASSWORD_RESET_OTPS.pop(clean_email, None)
                    return {"success": True, "user_id": payload.get("sub")}
            except Exception:
                pass

        if not record:
            return {"success": False, "message": "Invalid or expired password reset code. Please request a new one."}

        if datetime.now(timezone.utc) > record["exp"]:
            _PASSWORD_RESET_OTPS.pop(clean_email, None)
            return {"success": False, "message": "Password reset code has expired. Please request a new one."}

        clean_code = "".join(ch for ch in code_or_token if ch.isdigit())
        if record["code"] == clean_code:
            user_id = record["user_id"]
            _PASSWORD_RESET_OTPS.pop(clean_email, None)
            _PASSWORD_RESET_OTPS.pop(user_id, None)
            return {"success": True, "user_id": user_id}

        record["attempts"] = record.get("attempts", 0) + 1
        return {"success": False, "message": "Invalid verification code. Please check your code and try again."}

    def update_user_password(self, user_id: str, new_password_hash: str) -> bool:
        """Update user password hash across Supabase and SQLite."""
        # 1. Update in Supabase
        try:
            with httpx.Client(timeout=8.0) as client:
                client.patch(
                    f"{self.url}/rest/v1/users?id=eq.{user_id}",
                    json={"password_hash": new_password_hash},
                    headers=self.headers
                )
        except Exception:
            pass

        # 2. Update in SQLite
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "grantfinder.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))
                conn.commit()
                conn.close()
        except Exception:
            pass

        return True

    # ==========================================================================
    # Supabase Storage Avatars
    # ==========================================================================

    def upload_avatar(
        self,
        user_id: str,
        file_bytes: bytes,
        file_ext: str,
        content_type: str = "image/png"
    ) -> str:
        """Upload avatar image directly to Supabase Storage public 'avatars' bucket."""
        clean_ext = file_ext.lstrip('.').lower()
        if clean_ext == "jpg":
            clean_ext = "jpeg"
        target_path = f"{user_id}/avatar.{clean_ext}"
        storage_url = f"{self.url}/storage/v1/object/avatars/{target_path}"
        public_url = f"{self.url}/storage/v1/object/public/avatars/{target_path}"
        
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": content_type,
            "x-upsert": "true"
        }

        # Attempt to upload to Supabase Storage
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(storage_url, headers=headers, content=file_bytes)
                if res.status_code in (200, 201):
                    _USER_AVATARS[user_id] = public_url
                    return public_url
        except Exception:
            pass

        # Resilient local fallback
        local_dir = os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "avatars")
        os.makedirs(local_dir, exist_ok=True)
        local_filename = f"{user_id}_avatar.{clean_ext}"
        local_filepath = os.path.join(local_dir, local_filename)
        with open(local_filepath, "wb") as f:
            f.write(file_bytes)
        local_url = f"/static/uploads/avatars/{local_filename}"
        _USER_AVATARS[user_id] = local_url
        return local_url

    def delete_avatar(self, user_id: str) -> bool:
        """Delete avatar from Supabase Storage and fallback cache."""
        _USER_AVATARS[user_id] = ""
        for ext in ["png", "jpeg", "jpg", "webp"]:
            target_path = f"{user_id}/avatar.{ext}"
            storage_url = f"{self.url}/storage/v1/object/avatars/{target_path}"
            headers = {
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}"
            }
            try:
                with httpx.Client(timeout=8.0) as client:
                    client.delete(storage_url, headers=headers)
            except Exception:
                pass
        return True

    def get_avatar_url(self, user_id: str) -> Optional[str]:
        """Retrieve user avatar public URL."""
        if user_id in _USER_AVATARS and _USER_AVATARS[user_id]:
            return _USER_AVATARS[user_id]

        # Check storage bucket for existing file
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }
        try:
            with httpx.Client(timeout=6.0) as client:
                res = client.post(
                    f"{self.url}/storage/v1/object/list/avatars",
                    headers=headers,
                    json={"prefix": f"{user_id}/", "limit": 5}
                )
                if res.status_code == 200:
                    items = res.json()
                    if items and len(items) > 0:
                        file_name = items[0].get("name")
                        if file_name:
                            url = f"{self.url}/storage/v1/object/public/avatars/{user_id}/{file_name}"
                            _USER_AVATARS[user_id] = url
                            return url
        except Exception:
            pass

        return None

    # ==========================================================================
    # User Profiles (public.profiles)
    # ==========================================================================

    def upsert_profile(
        self,
        user_id: str,
        profile_type: str = "academic",
        major_or_domain: str = "General",
        degree_level_or_stage: str = "Undergraduate",
        semester: Optional[str] = None,
        country_preference: str = "Pakistan",
        gpa_funding: Optional[str] = None,
        extra_details: Optional[Dict[str, Any]] = None,
        avatar_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Insert or update user profile in Supabase public.profiles."""
        if avatar_url:
            _USER_AVATARS[user_id] = avatar_url

        existing = self.get_profile_by_user_id(user_id)
        clean_ptype = "startup" if profile_type in ("founder", "startup") else "academic"
        payload = {
            "user_id": user_id,
            "profile_type": clean_ptype,
            "major_or_domain": major_or_domain,
            "degree_level_or_stage": degree_level_or_stage,
            "semester": semester or (gpa_funding or ""),
            "country_preference": country_preference
        }

        # Attempt to include avatar_url if provided
        if avatar_url:
            payload["avatar_url"] = avatar_url

        # Cache extra_details if provided
        if extra_details:
            _USER_EXTRA_DETAILS[user_id] = {**_USER_EXTRA_DETAILS.get(user_id, {}), **extra_details}

        data = None
        try:
            with httpx.Client(timeout=3.0) as client:
                if existing and existing.get("id"):
                    pid = existing["id"]
                    try:
                        res = client.patch(
                            f"{self.url}/rest/v1/profiles?id=eq.{pid}",
                            json=payload,
                            headers=self.headers
                        )
                        res.raise_for_status()
                    except Exception:
                        # If avatar_url column does not exist yet in SQL, retry without it
                        payload.pop("avatar_url", None)
                        res = client.patch(
                            f"{self.url}/rest/v1/profiles?id=eq.{pid}",
                            json=payload,
                            headers=self.headers
                        )
                else:
                    pid = str(uuid.uuid4())
                    payload["id"] = pid
                    try:
                        res = client.post(
                            f"{self.url}/rest/v1/profiles",
                            json=payload,
                            headers=self.headers
                        )
                        res.raise_for_status()
                    except Exception:
                        payload.pop("avatar_url", None)
                        res = client.post(
                            f"{self.url}/rest/v1/profiles",
                            json=payload,
                            headers=self.headers
                        )

                if res.status_code in (200, 201):
                    data = res.json()
        except Exception:
            pass

        effective_avatar = avatar_url or self.get_avatar_url(user_id)
        merged_extra = {**(extra_details or {}), **_USER_EXTRA_DETAILS.get(user_id, {})}
        user = self.get_user_by_id(user_id) or {}

        if data and len(data) > 0:
            row = data[0]
            row["type"] = row.get("profile_type")
            row["major_domain"] = row.get("major_or_domain")
            row["degree_level_stage"] = row.get("degree_level_or_stage")
            row["gpa_funding"] = row.get("semester")
            row["avatar_url"] = effective_avatar
            row["extra_details"] = merged_extra
            row["university"] = merged_extra.get("university", "")
            row["cgpa"] = merged_extra.get("cgpa", "")
            row["city"] = merged_extra.get("city", "")
            row["grad_year"] = merged_extra.get("grad_year", "")
            row["test_scores"] = merged_extra.get("test_scores", "")
            row["financial_need"] = merged_extra.get("financial_need", "No")
            row["onboarding_completed"] = merged_extra.get("onboarding_completed", True)
            row["completion_pct"] = self.calculate_profile_completion_pct(user, row)
            _USER_PROFILES[user_id] = row
            return row

        payload["type"] = profile_type
        payload["major_domain"] = major_or_domain
        payload["degree_level_stage"] = degree_level_or_stage
        payload["gpa_funding"] = semester or (gpa_funding or "")
        payload["avatar_url"] = effective_avatar
        payload["extra_details"] = merged_extra
        payload["university"] = merged_extra.get("university", "")
        payload["cgpa"] = merged_extra.get("cgpa", "")
        payload["city"] = merged_extra.get("city", "")
        payload["grad_year"] = merged_extra.get("grad_year", "")
        payload["test_scores"] = merged_extra.get("test_scores", "")
        payload["financial_need"] = merged_extra.get("financial_need", "No")
        payload["onboarding_completed"] = merged_extra.get("onboarding_completed", True)
        payload["completion_pct"] = self.calculate_profile_completion_pct(user, payload)
        _USER_PROFILES[user_id] = payload
        return payload

    def calculate_profile_completion_pct(self, user: Dict[str, Any], profile: Optional[Dict[str, Any]]) -> int:
        """Calculate profile completion percentage (60% core baseline up to 100% full)."""
        if not profile:
            return 0
        extra = profile.get("extra_details") or {}
        
        score = 0
        # Core fields (60% total)
        if user.get("name"):
            score += 10
        if user.get("email"):
            score += 10
        if profile.get("major_domain"):
            score += 10
        if profile.get("degree_level_stage"):
            score += 10
        if profile.get("semester") or profile.get("gpa_funding") or extra.get("semester_or_funding"):
            score += 10
        if profile.get("country_preference"):
            score += 10
            
        # Optional fields (40% total)
        if profile.get("avatar_url") or _USER_AVATARS.get(user.get("id")):
            score += 10
        if extra.get("university"):
            score += 10
        if extra.get("cgpa"):
            score += 10
        if extra.get("city") or extra.get("grad_year") or extra.get("test_scores") or (extra.get("financial_need") and extra.get("financial_need") != "No"):
            score += 10
            
        return min(100, max(0, score))

    def get_profile_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Query user profile from Supabase public.profiles or in-memory fallback."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(
                    f"{self.url}/rest/v1/profiles?user_id=eq.{user_id}&select=*",
                    headers=self.headers
                )
                if res.status_code == 200:
                    data = res.json()
                    if data and len(data) > 0:
                        row = data[0]
                        # Map canonical keys for backward compatibility
                        row["type"] = row.get("profile_type")
                        row["major_domain"] = row.get("major_or_domain")
                        row["degree_level_stage"] = row.get("degree_level_or_stage")
                        row["gpa_funding"] = row.get("semester")
                        row["avatar_url"] = row.get("avatar_url") or self.get_avatar_url(user_id)
                        
                        extra = row.get("extra_details") if isinstance(row.get("extra_details"), dict) else {}
                        merged_extra = {**extra, **_USER_EXTRA_DETAILS.get(user_id, {})}
                        row["extra_details"] = merged_extra
                        row["university"] = merged_extra.get("university", "")
                        row["cgpa"] = merged_extra.get("cgpa", "")
                        row["city"] = merged_extra.get("city", "")
                        row["grad_year"] = merged_extra.get("grad_year", "")
                        row["test_scores"] = merged_extra.get("test_scores", "")
                        row["financial_need"] = merged_extra.get("financial_need", "No")
                        row["onboarding_completed"] = merged_extra.get("onboarding_completed", True)
                        
                        user = self.get_user_by_id(user_id) or {}
                        row["completion_pct"] = self.calculate_profile_completion_pct(user, row)
                        _USER_PROFILES[user_id] = row
                        return row
        except Exception:
            pass

        if user_id in _USER_PROFILES:
            return _USER_PROFILES[user_id]
        return None

    # ==========================================================================
    # Saved Opportunities (public.saved_opportunities)
    # ==========================================================================

    def save_opportunity(
        self,
        user_id: str,
        opportunity_name: str,
        source_link: Optional[str] = None,
        match_score: int = 80,
        opportunity_type: Optional[str] = None,
        amount: Optional[str] = None,
        deadline: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save an opportunity into Supabase public.saved_opportunities."""
        sid = str(uuid.uuid4())
        payload = {
            "id": sid,
            "user_id": user_id,
            "opportunity_name": opportunity_name,
            "source_link": source_link or "https://example.com",
            "match_score": match_score
        }
        with httpx.Client(timeout=8.0) as client:
            res = client.post(
                f"{self.url}/rest/v1/saved_opportunities",
                json=payload,
                headers=self.headers
            )
            res.raise_for_status()
            data = res.json()
            if data and len(data) > 0:
                item = data[0]
                item["opportunity_type"] = opportunity_type or "scholarship"
                item["amount"] = amount or "Funded"
                item["deadline"] = deadline or "Open"
                return item
            payload["opportunity_type"] = opportunity_type or "scholarship"
            payload["amount"] = amount or "Funded"
            payload["deadline"] = deadline or "Open"
            payload["saved_date"] = datetime.now(timezone.utc).isoformat()
            return payload

    def get_saved_opportunities(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve saved opportunities for a user from Supabase."""
        with httpx.Client(timeout=8.0) as client:
            res = client.get(
                f"{self.url}/rest/v1/saved_opportunities?user_id=eq.{user_id}&order=saved_date.desc",
                headers=self.headers
            )
            if res.status_code == 200:
                items = res.json()
                for it in items:
                    it["name"] = it.get("opportunity_name")
                    it["type"] = it.get("opportunity_type", "scholarship")
                    it["amount"] = it.get("amount", "Funded")
                    it["deadline"] = it.get("deadline", "Open")
                return items
            return []

    def delete_saved_opportunity(self, user_id: str, saved_id: str) -> bool:
        """Delete saved opportunity from Supabase."""
        with httpx.Client(timeout=8.0) as client:
            res = client.delete(
                f"{self.url}/rest/v1/saved_opportunities?id=eq.{saved_id}&user_id=eq.{user_id}",
                headers=self.headers
            )
            return res.status_code in (200, 204)

    # ==========================================================================
    # Curated Opportunities (public.curated_opportunities)
    # ==========================================================================

    def list_curated_opportunities(
        self,
        track: Optional[str] = None,
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List curated opportunities from Supabase public.curated_opportunities."""
        query_params = ["select=*"]
        if track and track.lower() != "all":
            query_params.append(f"opportunity_type=eq.{track.lower()}")
        if country and country.lower() != "all":
            query_params.append(f"country=in.({country},International)")

        qs = "&".join(query_params)
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.get(
                    f"{self.url}/rest/v1/curated_opportunities?{qs}&order=deadline.asc",
                    headers=self.headers
                )
                if res.status_code == 200:
                    raw_items = res.json()
                    results = []
                    for it in raw_items:
                        item = dict(it)
                        item["type"] = item.get("opportunity_type")
                        item["category"] = item.get("category", "General")
                        item["domains"] = []
                        item["stages"] = []
                        results.append(item)
                    return results
        except Exception:
            pass

        # Fallback to local curated_opportunities.json
        try:
            data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "curated_opportunities.json")
            if os.path.exists(data_path):
                with open(data_path, "r", encoding="utf-8") as f:
                    local_items = json.load(f)
                    filtered = []
                    for item in local_items:
                        if track and track.lower() != "all" and item.get("type", "").lower() != track.lower():
                            continue
                        if country and country.lower() != "all":
                            c_item = (item.get("country") or "").lower()
                            c_req = country.lower()
                            if c_item not in (c_req, "international", "global") and c_req not in c_item:
                                continue
                        filtered.append(dict(item))
                    return filtered
        except Exception:
            pass

        return []

    def add_curated_opportunity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a curated opportunity into Supabase."""
        cid = str(uuid.uuid4())
        payload = {
            "id": cid,
            "name": data["name"],
            "opportunity_type": data.get("type") or data.get("opportunity_type", "scholarship"),
            "country": data.get("country", "Pakistan"),
            "amount": data.get("amount", "Funded"),
            "deadline": data.get("deadline"),
            "eligibility": data.get("eligibility", "General"),
            "source_link": data.get("source_link", "https://example.com")
        }
        with httpx.Client(timeout=8.0) as client:
            res = client.post(
                f"{self.url}/rest/v1/curated_opportunities",
                json=payload,
                headers=self.headers
            )
            res.raise_for_status()
            d = res.json()
            return d[0] if d else payload

    def delete_curated_opportunity(self, opp_id: str) -> bool:
        """Delete curated opportunity from Supabase."""
        with httpx.Client(timeout=8.0) as client:
            res = client.delete(
                f"{self.url}/rest/v1/curated_opportunities?id=eq.{opp_id}",
                headers=self.headers
            )
            return res.status_code in (200, 204)

    # ==========================================================================
    # Unified Notifications (public.notifications)
    # ==========================================================================

    def insert_notification(
        self,
        user_id: str,
        message: str,
        channel: str
    ) -> Dict[str, Any]:
        """Insert notification directly into Supabase public.notifications.
        Channel must strictly be one of: 'in_app', 'email', 'whatsapp'.
        """
        valid_channels = {"in_app", "email", "whatsapp"}
        clean_channel = channel.replace("-", "_")
        if clean_channel not in valid_channels:
            clean_channel = "in_app"

        nid = str(uuid.uuid4())
        payload = {
            "id": nid,
            "user_id": user_id,
            "message": message,
            "channel": clean_channel,
            "title": "GrantFinder Alert",
            "is_read": False,
            "sent_date": datetime.now(timezone.utc).isoformat()
        }

        # Dual-write into in-memory notification queue for instant resilience
        if user_id not in _IN_APP_NOTIFICATIONS:
            _IN_APP_NOTIFICATIONS[user_id] = []
        _IN_APP_NOTIFICATIONS[user_id].insert(0, dict(payload))

        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.post(
                    f"{self.url}/rest/v1/notifications",
                    json={"id": nid, "user_id": user_id, "message": message, "channel": clean_channel},
                    headers=self.headers
                )
                if res.status_code in (200, 201):
                    data = res.json()
                    return data[0] if data else payload
        except Exception:
            pass
        return payload

    def get_user_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch latest notifications for user from Supabase or memory."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(
                    f"{self.url}/rest/v1/notifications?user_id=eq.{user_id}&order=sent_date.desc&limit=20",
                    headers=self.headers
                )
                if res.status_code == 200:
                    items = res.json()
                    if items and len(items) > 0:
                        for it in items:
                            it["title"] = "GrantFinder Alert"
                        return items
        except Exception:
            pass

        # Fallback to local memory notifications
        return _IN_APP_NOTIFICATIONS.get(user_id, [])

    def mark_notification_read(self, notification_id: str, user_id: Optional[str] = None) -> bool:
        """Mark notification read in Supabase and memory."""
        if user_id and user_id in _IN_APP_NOTIFICATIONS:
            for n in _IN_APP_NOTIFICATIONS[user_id]:
                if n.get("id") == notification_id:
                    n["is_read"] = True
        else:
            for uid, notes in _IN_APP_NOTIFICATIONS.items():
                for n in notes:
                    if n.get("id") == notification_id:
                        n["is_read"] = True

        try:
            url = f"{self.url}/rest/v1/notifications?id=eq.{notification_id}"
            if user_id:
                url += f"&user_id=eq.{user_id}"
            with httpx.Client(timeout=3.0) as client:
                res = client.patch(
                    url,
                    json={"is_read": True},
                    headers=self.headers
                )
                return res.status_code in (200, 204)
        except Exception:
            return True

    # ==========================================================================
    # Chat History (public.chat_history)
    # ==========================================================================

    async def save_chat_message(
        self,
        session_id: str = "default_session",
        role: str = "user",
        content: str = "",
        user_id: Optional[str] = None,
        message: Optional[str] = None
    ) -> bool:
        """Persist a chat turn to Supabase public.chat_history."""
        msg_text = content or message or ""
        clean_user_id = None
        # Verify valid UUID if user_id is provided
        if user_id:
            try:
                uuid.UUID(str(user_id))
                clean_user_id = str(user_id)
            except ValueError:
                clean_user_id = None

        payload = {
            "id": str(uuid.uuid4()),
            "user_id": clean_user_id,
            "role": role,
            "message": msg_text
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(
                    f"{self.url}/rest/v1/chat_history",
                    json=payload,
                    headers=self.headers
                )
                return res.status_code in (200, 201)
        except Exception:
            return False

supabase_service = SupabaseService()
