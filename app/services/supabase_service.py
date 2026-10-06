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

class SupabaseService:
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
        plan: str = "free"
    ) -> Dict[str, Any]:
        """Insert a newly registered user directly into Supabase public.users."""
        user_id = str(uuid.uuid4())
        payload = {
            "id": user_id,
            "name": name.strip(),
            "email": email.strip().lower(),
            "password_hash": password_hash,
            "role": role,
            "plan": plan
        }
        with httpx.Client(timeout=8.0) as client:
            res = client.post(
                f"{self.url}/rest/v1/users",
                json=payload,
                headers=self.headers
            )
            res.raise_for_status()
            data = res.json()
            if data and len(data) > 0:
                return data[0]
            payload["created_at"] = datetime.now(timezone.utc).isoformat()
            return payload

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Query user record from Supabase public.users by email."""
        clean_email = email.strip().lower()
        with httpx.Client(timeout=8.0) as client:
            res = client.get(
                f"{self.url}/rest/v1/users?email=eq.{clean_email}&select=*",
                headers=self.headers
            )
            if res.status_code == 200:
                data = res.json()
                if data and len(data) > 0:
                    return data[0]
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Query user record from Supabase public.users by UUID."""
        with httpx.Client(timeout=8.0) as client:
            res = client.get(
                f"{self.url}/rest/v1/users?id=eq.{user_id}&select=*",
                headers=self.headers
            )
            if res.status_code == 200:
                data = res.json()
                if data and len(data) > 0:
                    return data[0]
            return None

    def update_user_plan(self, user_id: str, new_plan: str) -> bool:
        """Update subscription plan in Supabase public.users."""
        with httpx.Client(timeout=8.0) as client:
            res = client.patch(
                f"{self.url}/rest/v1/users?id=eq.{user_id}",
                json={"plan": new_plan},
                headers=self.headers
            )
            return res.status_code in (200, 204)

    def list_all_users(self) -> List[Dict[str, Any]]:
        """List all users ordered by creation date descending."""
        with httpx.Client(timeout=8.0) as client:
            res = client.get(
                f"{self.url}/rest/v1/users?select=id,name,email,role,plan,created_at&order=created_at.desc",
                headers=self.headers
            )
            if res.status_code == 200:
                return res.json()
            return []

    def update_user_details(
        self,
        user_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update user name, email, and/or role in Supabase public.users."""
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
            with httpx.Client(timeout=8.0) as client:
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

        with httpx.Client(timeout=8.0) as client:
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

            res.raise_for_status()
            data = res.json()
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
        """Query user profile from Supabase public.profiles."""
        with httpx.Client(timeout=8.0) as client:
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
                    return row
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
            "channel": clean_channel
        }
        with httpx.Client(timeout=8.0) as client:
            res = client.post(
                f"{self.url}/rest/v1/notifications",
                json=payload,
                headers=self.headers
            )
            res.raise_for_status()
            data = res.json()
            return data[0] if data else payload

    def get_user_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch latest notifications for user from Supabase."""
        with httpx.Client(timeout=8.0) as client:
            res = client.get(
                f"{self.url}/rest/v1/notifications?user_id=eq.{user_id}&order=sent_date.desc&limit=20",
                headers=self.headers
            )
            if res.status_code == 200:
                items = res.json()
                for it in items:
                    it["title"] = "GrantFinder Alert"
                return items
            return []

    def mark_notification_read(self, notification_id: str, user_id: Optional[str] = None) -> bool:
        """Mark notification read in Supabase."""
        url = f"{self.url}/rest/v1/notifications?id=eq.{notification_id}"
        if user_id:
            url += f"&user_id=eq.{user_id}"
        with httpx.Client(timeout=8.0) as client:
            res = client.patch(
                url,
                json={"is_read": True},
                headers=self.headers
            )
            return res.status_code in (200, 204)

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
