import os
from typing import Dict, Any, Optional, List
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.config import settings
from app.services.supabase_service import supabase_service

# Locate templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True
)

class EmailTemplateService:
    """Professional, role-based HTML and plain-text email template engine for GrantFinder AI."""

    @staticmethod
    def resolve_user_role(user: Dict[str, Any], profile: Optional[Dict[str, Any]] = None) -> str:
        """Automatically resolve user role family: 'founder' vs 'student'.
        Checks user['role'] and profile['type'] / profile['profile_type'].
        Never hardcoded per call.
        """
        user_role = (user.get("role") or "").strip().lower()
        if user_role in ("founder", "startup"):
            return "founder"

        if profile:
            ptype = (profile.get("profile_type") or profile.get("type") or "").strip().lower()
            if ptype in ("founder", "startup"):
                return "founder"

        # If user record has extra_details indicating a founder
        extra = user.get("extra_details") or (profile.get("extra_details") if profile else {})
        if isinstance(extra, dict) and extra.get("startup_name"):
            return "founder"

        return "student"

    @staticmethod
    def build_subject_line(role: str, alert_type: str, opportunity_name: str, match_score: Optional[int] = None, days_left: Optional[int] = None) -> str:
        """Construct role-calibrated email subject line."""
        score_suffix = f" ({match_score}% Match)" if match_score else ""
        
        if role == "founder":
            if alert_type == "deadline_approaching":
                time_str = f"{days_left} Days Left" if days_left else "Closing Soon"
                return f"[GrantFinder AI] Funding Deadline Alert: {time_str} for {opportunity_name}"
            elif alert_type == "weekly_digest":
                return "[GrantFinder AI] Your Weekly Startup Grant Digest: Top Curated Funding Opportunities"
            else:
                return f"[GrantFinder AI] New Startup Grant Match: {opportunity_name}{score_suffix}"
        else:
            if alert_type == "deadline_approaching":
                time_str = f"{days_left} Days Left" if days_left else "Closing Soon"
                return f"[GrantFinder AI] Deadline Alert: {time_str} for {opportunity_name}"
            elif alert_type == "weekly_digest":
                return "[GrantFinder AI] Your Weekly Scholarship Digest: Top Curated Opportunities"
            else:
                return f"[GrantFinder AI] New Scholarship Match: {opportunity_name}{score_suffix}"

    @classmethod
    def render_email_alert(
        cls,
        user: Dict[str, Any],
        alert_type: str = "new_match",
        opportunity_data: Optional[Dict[str, Any]] = None,
        opportunities_list: Optional[List[Dict[str, Any]]] = None,
        profile: Optional[Dict[str, Any]] = None,
        base_url: str = ""
    ) -> Dict[str, Any]:
        """Render role-specific HTML and plain-text email with dynamic personalization.
        Works across all three alert types: 'new_match', 'deadline_approaching', 'weekly_digest'.
        """
        user_id = str(user.get("id") or "user-preview")
        email = str(user.get("email") or "applicant@grantfinder.ai").strip().lower()
        full_name = str(user.get("name") or "Applicant").strip()
        first_name = full_name.split()[0] if full_name else "Applicant"

        # Attempt to load profile if not supplied
        if not profile and user.get("id"):
            try:
                profile = supabase_service.get_profile_by_user_id(user["id"])
            except Exception:
                profile = None

        role = cls.resolve_user_role(user, profile)
        domain = base_url.rstrip("/") if base_url else "https://grantfinder-ai.onrender.com"

        # Unsubscribe token and link
        unsub_token = supabase_service.generate_subscription_token(user_id, email, action="unsubscribe")
        unsubscribe_link = f"{domain}/api/notifications/unsubscribe?token={unsub_token}"
        dashboard_link = f"{domain}/dashboard"

        # Extract primary opportunity data
        opp = dict(opportunity_data or {})
        opp_name = opp.get("opportunity_name") or opp.get("name") or opp.get("title") or (
            "Curated Innovation Grant" if role == "founder" else "Curated Academic Scholarship"
        )
        match_score = opp.get("match_score")
        if match_score is None:
            match_score = 92 if role == "founder" else 94

        days_left = opp.get("days_left")
        if days_left is None and alert_type == "deadline_approaching":
            days_left = 7

        # Extract founder-specific metadata
        startup_domain = None
        if role == "founder":
            if profile and profile.get("major_or_domain") and profile.get("major_or_domain") not in ("General", "N/A"):
                startup_domain = profile.get("major_or_domain")
            elif opp.get("domain") or opp.get("startup_domain"):
                startup_domain = opp.get("domain") or opp.get("startup_domain")

        subject = cls.build_subject_line(role, alert_type, opp_name, match_score, days_left)

        # Context mapping for Jinja2 template
        context: Dict[str, Any] = {
            "subject": subject,
            "header_badge": (
                "Startup Grant Alert" if role == "founder" and alert_type == "new_match" else
                "Scholarship Alert" if role == "student" and alert_type == "new_match" else
                "Deadline Reminder" if alert_type == "deadline_approaching" else
                "Weekly Funding Digest"
            ),
            "first_name": first_name,
            "full_name": full_name,
            "role": role,
            "alert_type": alert_type,
            "opportunity_name": opp_name,
            "country": opp.get("country") or opp.get("region"),
            "amount": opp.get("amount") or opp.get("funding_amount"),
            "deadline": opp.get("deadline") or ("June 30, 2026" if alert_type == "deadline_approaching" else "Rolling"),
            "days_left": days_left,
            "match_score": match_score,
            "match_reason": opp.get("match_reason") or (
                f"Calibrated for your {startup_domain or 'venture'} focus, milestone stage, and capital requirements."
                if role == "founder" else
                "Calibrated for your academic field, degree level, and eligibility requirements."
            ),
            "source_link": opp.get("source_link") or opp.get("url") or f"{domain}/destinations",
            "dashboard_link": dashboard_link,
            "unsubscribe_link": unsubscribe_link,
            "intro_text": opp.get("intro_text")
        }

        # Track-specific CTAs & fields
        if role == "founder":
            context["funder"] = opp.get("funder") or opp.get("organization") or "Global Innovation Fund"
            context["stage_fit"] = opp.get("stage_fit") or opp.get("stage") or (profile.get("degree_level_or_stage") if profile else "Prototype / Seed")
            context["equity_type"] = opp.get("equity_type") or "0% Equity Non-Dilutive Grant"
            context["startup_domain"] = startup_domain
            context["pitch_link"] = f"{domain}/ai-assistant?opp={opp_name}&type=pitch"
            template_name = "emails/founder_alert.html"
        else:
            context["degree_level"] = opp.get("degree_level") or (profile.get("degree_level_or_stage") if profile else "Undergraduate / Graduate")
            context["cgpa_fit"] = opp.get("cgpa_fit") or "Minimum 3.00 CGPA Aligned"
            context["funding_type"] = opp.get("funding_type") or "Fully Funded Tuition & Stipend"
            context["essay_link"] = f"{domain}/ai-assistant?opp={opp_name}&type=essay"
            template_name = "emails/student_alert.html"

        # Weekly digest multiple opportunities
        if opportunities_list:
            context["opportunities"] = opportunities_list
        elif alert_type == "weekly_digest" and not opportunities_list:
            # Provide sample digest secondary entries if none provided
            if role == "founder":
                context["opportunities"] = [
                    {"opportunity_name": opp_name, "funder": context.get("funder"), "amount": context.get("amount"), "deadline": context.get("deadline"), "match_score": match_score},
                    {"opportunity_name": "Ignite National Technology Fund", "funder": "Ministry of IT", "amount": "PKR 5,000,000", "deadline": "August 15, 2026", "match_score": 89},
                    {"opportunity_name": "Climate Action Seed Accelerator", "funder": "UN Innovation Lab", "amount": "USD 25,000", "deadline": "September 1, 2026", "match_score": 84}
                ]
            else:
                context["opportunities"] = [
                    {"opportunity_name": opp_name, "country": context.get("country"), "amount": context.get("amount"), "deadline": context.get("deadline"), "match_score": match_score},
                    {"opportunity_name": "Fulbright Foreign Student Program", "country": "United States", "amount": "Fully Funded", "deadline": "October 10, 2026", "match_score": 91},
                    {"opportunity_name": "DAAD Development-Related Postgraduate Grants", "country": "Germany", "amount": "EUR 1,200/mo + Travel", "deadline": "November 15, 2026", "match_score": 87}
                ]

        # Render HTML
        template = _jinja_env.get_template(template_name)
        html_content = template.render(**context)

        # Generate Plain-Text Fallback
        text_content = cls.generate_plaintext_fallback(role, alert_type, context)

        return {
            "subject": subject,
            "html": html_content,
            "text": text_content,
            "role": role,
            "alert_type": alert_type,
            "context": context
        }

    @classmethod
    def generate_plaintext_fallback(cls, role: str, alert_type: str, context: Dict[str, Any]) -> str:
        """Produce a clean, accessible plain-text alternative alongside the HTML email."""
        first_name = context.get("first_name", "Applicant")
        opp_name = context.get("opportunity_name", "Curated Opportunity")
        match_score = context.get("match_score", "")
        amount = context.get("amount")
        deadline = context.get("deadline")
        days_left = context.get("days_left")
        country = context.get("country")
        match_reason = context.get("match_reason")
        source_link = context.get("source_link", "")
        dashboard_link = context.get("dashboard_link", "")
        unsub_link = context.get("unsubscribe_link", "")

        lines: List[str] = []
        if role == "founder":
            lines.append("GRANTFINDER AI | STARTUP GRANT ALERT")
            lines.append("=" * 60)
            domain_greeting = f" - new {context['startup_domain']} funding for your venture" if context.get("startup_domain") else ""
            lines.append(f"Dear {first_name}{domain_greeting},\n")

            if alert_type == "deadline_approaching":
                lines.append(f"Time-sensitive funding notice: The submission window for this grant closes in {days_left or 'few'} days.")
            elif alert_type == "weekly_digest":
                lines.append("Here is your weekly curated venture funding digest of top startup grant matches.")
            else:
                lines.append("Our venture matching engine has identified an active startup grant matched to your profile.")

            lines.append("\nGRANT DETAILS:")
            lines.append(f"- Program: {opp_name}")
            if context.get("funder"):
                lines.append(f"- Funder: {context['funder']}")
            if match_score:
                lines.append(f"- Match Score: {match_score}% Compatibility Match")
            if amount:
                lines.append(f"- Grant Amount: {amount}")
            if context.get("stage_fit"):
                lines.append(f"- Stage Fit: {context['stage_fit']}")
            if context.get("equity_type"):
                lines.append(f"- Equity: {context['equity_type']}")
            if country:
                lines.append(f"- Region: {country}")
            if deadline:
                deadline_str = f"{deadline} ({days_left} days left)" if days_left else str(deadline)
                lines.append(f"- Deadline: {deadline_str}")

            if match_reason:
                lines.append(f"\nVENTURE ALIGNMENT:\n{match_reason}")

            lines.append("\nNEXT STEPS:")
            lines.append(f"- View Grant Details: {source_link}")
            lines.append(f"- Generate Pitch Draft: {context.get('pitch_link', dashboard_link)}")

        else:
            lines.append("GRANTFINDER AI | SCHOLARSHIP ALERT")
            lines.append("=" * 60)
            lines.append(f"Dear {first_name},\n")

            if alert_type == "deadline_approaching":
                lines.append(f"Application deadline notice: The submission window for this scholarship closes in {days_left or 'few'} days.")
            elif alert_type == "weekly_digest":
                lines.append("Here is your weekly curated scholarship digest of top academic opportunities.")
            else:
                lines.append("Our semantic matching engine has identified a scholarship opportunity matched to your academic record.")

            lines.append("\nSCHOLARSHIP DETAILS:")
            lines.append(f"- Scholarship: {opp_name}")
            if match_score:
                lines.append(f"- Match Score: {match_score}% Compatibility Match")
            if country:
                lines.append(f"- Study Destination: {country}")
            if amount:
                lines.append(f"- Funding Coverage: {amount}")
            if context.get("degree_level"):
                lines.append(f"- Degree Level: {context['degree_level']}")
            if context.get("cgpa_fit"):
                lines.append(f"- Academic Fit: {context['cgpa_fit']}")
            if deadline:
                deadline_str = f"{deadline} ({days_left} days left)" if days_left else str(deadline)
                lines.append(f"- Deadline: {deadline_str}")

            if match_reason:
                lines.append(f"\nELIGIBILITY ALIGNMENT:\n{match_reason}")

            lines.append("\nNEXT STEPS:")
            lines.append(f"- View Scholarship Details: {source_link}")
            lines.append(f"- Generate Essay Draft: {context.get('essay_link', dashboard_link)}")

        lines.append("\n" + "=" * 60)
        lines.append("You are receiving this curated notification because your account is verified on the GrantFinder AI Premium Tier.")
        lines.append(f"Unsubscribe from email alerts: {unsub_link}")
        lines.append(f"Manage notification preferences: {dashboard_link}")
        lines.append("(c) 2026 GrantFinder AI. All rights reserved.")

        return "\n".join(lines)

email_template_service = EmailTemplateService()
