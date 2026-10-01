import os
import uuid
import json
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.config import settings

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
        extra_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Insert or update user profile in Supabase public.profiles."""
        existing = self.get_profile_by_user_id(user_id)
        payload = {
            "user_id": user_id,
            "profile_type": profile_type,
            "major_or_domain": major_or_domain,
            "degree_level_or_stage": degree_level_or_stage,
            "semester": semester or (gpa_funding or ""),
            "country_preference": country_preference
        }
        with httpx.Client(timeout=8.0) as client:
            if existing and existing.get("id"):
                pid = existing["id"]
                res = client.patch(
                    f"{self.url}/rest/v1/profiles?id=eq.{pid}",
                    json=payload,
                    headers=self.headers
                )
            else:
                pid = str(uuid.uuid4())
                payload["id"] = pid
                res = client.post(
                    f"{self.url}/rest/v1/profiles",
                    json=payload,
                    headers=self.headers
                )
            res.raise_for_status()
            data = res.json()
            if data and len(data) > 0:
                row = data[0]
                row["type"] = row.get("profile_type")
                row["major_domain"] = row.get("major_or_domain")
                row["degree_level_stage"] = row.get("degree_level_or_stage")
                row["gpa_funding"] = row.get("semester")
                row["extra_details"] = extra_details or {}
                return row
            payload["type"] = profile_type
            payload["major_domain"] = major_or_domain
            payload["degree_level_stage"] = degree_level_or_stage
            payload["gpa_funding"] = semester or (gpa_funding or "")
            payload["extra_details"] = extra_details or {}
            return payload

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
                    row["extra_details"] = {}
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
