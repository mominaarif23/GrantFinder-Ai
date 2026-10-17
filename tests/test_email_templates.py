import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.services.email_template_service import email_template_service, EmailTemplateService
from app.services.supabase_service import supabase_service
from app.services.notification_service import notify_user, send_templated_email

client = TestClient(app)

def test_role_resolution_logic():
    """Verify automatic user role resolution between 'student' and 'founder'."""
    # 1. Student by user role
    u1 = {"role": "student"}
    assert EmailTemplateService.resolve_user_role(u1) == "student"

    # 2. Founder by user role
    u2 = {"role": "founder"}
    assert EmailTemplateService.resolve_user_role(u2) == "founder"

    # 3. Founder by profile type
    u3 = {"role": "academic"}
    p3 = {"profile_type": "startup"}
    assert EmailTemplateService.resolve_user_role(u3, p3) == "founder"

    # 4. Student by academic profile
    u4 = {"role": ""}
    p4 = {"profile_type": "academic"}
    assert EmailTemplateService.resolve_user_role(u4, p4) == "student"

    # 5. Founder by extra details
    u5 = {"role": "student", "extra_details": {"startup_name": "AgriSense"}}
    assert EmailTemplateService.resolve_user_role(u5) == "founder"


def test_subject_line_construction():
    """Verify role and alert-type calibrated subject lines."""
    # Student subjects
    s_nm = EmailTemplateService.build_subject_line("student", "new_match", "Rhodes Scholarship", 95)
    assert "[GrantFinder AI] New Scholarship Match: Rhodes Scholarship (95% Match)" == s_nm

    s_dl = EmailTemplateService.build_subject_line("student", "deadline_approaching", "DAAD Grant", days_left=7)
    assert "[GrantFinder AI] Deadline Alert: 7 Days Left for DAAD Grant" == s_dl

    s_wd = EmailTemplateService.build_subject_line("student", "weekly_digest", "Top Scholarships")
    assert "[GrantFinder AI] Your Weekly Scholarship Digest: Top Curated Opportunities" == s_wd

    # Founder subjects
    f_nm = EmailTemplateService.build_subject_line("founder", "new_match", "Ignite Seed Grant", 92)
    assert "[GrantFinder AI] New Startup Grant Match: Ignite Seed Grant (92% Match)" == f_nm

    f_dl = EmailTemplateService.build_subject_line("founder", "deadline_approaching", "Climate Fund", days_left=1)
    assert "[GrantFinder AI] Funding Deadline Alert: 1 Days Left for Climate Fund" == f_dl

    f_wd = EmailTemplateService.build_subject_line("founder", "weekly_digest", "Top Grants")
    assert "[GrantFinder AI] Your Weekly Startup Grant Digest: Top Curated Funding Opportunities" == f_wd


def test_student_template_rendering_and_placeholders():
    """Verify student scholarship template rendering, first name greeting, and dual CTAs."""
    user = {
        "id": "student-qa-1",
        "name": "Momina Tariq",
        "email": "momina@example.com",
        "role": "student"
    }
    opp = {
        "opportunity_name": "Erasmus Mundus AI Fellowship",
        "country": "Germany & France",
        "amount": "EUR 1,400/month Stipend + Full Tuition",
        "degree_level": "Master of Science",
        "cgpa_fit": "3.80+ CGPA Aligned",
        "deadline": "November 30, 2026",
        "days_left": 44,
        "match_score": 96,
        "match_reason": "High affinity with your computer science background and international research goals."
    }

    res = email_template_service.render_email_alert(user, "new_match", opp)
    html = res["html"]
    text = res["text"]

    # Brand colours & structure
    assert "#1F4E5F" in html
    assert "#C28C2A" in html
    assert "#F8F9FA" in html

    # Personalization & greeting (first name only)
    assert "Dear Momina," in html
    assert "Dear Momina," in text

    # Fields
    assert "Erasmus Mundus AI Fellowship" in html
    assert ("Germany &amp; France" in html) or ("Germany & France" in html)
    assert "Germany & France" in text
    assert "EUR 1,400/month Stipend" in html
    assert "3.80+ CGPA Aligned" in html
    assert "96% Compatibility Match" in html

    # Dual CTAs for student
    assert "View Scholarship" in html
    assert "Generate Essay Draft" in html
    assert "View Scholarship Details:" in text
    assert "Generate Essay Draft:" in text

    # Unsubscribe link
    assert "/api/notifications/unsubscribe?token=" in html
    assert "/api/notifications/unsubscribe?token=" in text

    # Footer notice
    assert "GrantFinder AI Premium Tier" in html


def test_founder_template_rendering_and_domain_greeting():
    """Verify founder startup grant template rendering, startup domain in greeting, and dual CTAs."""
    user = {
        "id": "founder-qa-1",
        "name": "Hamza Tariq",
        "email": "hamza@example.com",
        "role": "founder"
    }
    profile = {
        "profile_type": "startup",
        "type": "startup",
        "major_or_domain": "AgriTech",
        "degree_level_stage": "Early Prototype / MVP"
    }
    opp = {
        "opportunity_name": "Bill & Melinda Gates Climate AgriTech Challenge",
        "funder": "Gates Foundation & CGIAR",
        "amount": "USD 100,000",
        "stage_fit": "Prototype / Seed Stage",
        "equity_type": "0% Equity Non-Dilutive Grant",
        "country": "Pakistan & South Asia",
        "deadline": "December 15, 2026",
        "days_left": 60,
        "match_score": 94,
        "match_reason": "Targeted at climate-smart crop yield optimization startups with working pilot data."
    }

    res = email_template_service.render_email_alert(user, "new_match", opp, profile=profile)
    html = res["html"]
    text = res["text"]

    # First name + domain in greeting
    assert "Dear Hamza" in html
    assert "new AgriTech funding discovered for your venture" in html
    assert "Dear Hamza - new AgriTech funding for your venture" in text

    # Founder fields
    assert ("Bill &amp; Melinda Gates Climate AgriTech Challenge" in html) or ("Bill & Melinda Gates Climate AgriTech Challenge" in html)
    assert "Bill & Melinda Gates Climate AgriTech Challenge" in text
    assert ("Gates Foundation &amp; CGIAR" in html) or ("Gates Foundation & CGIAR" in html)
    assert "Gates Foundation & CGIAR" in text
    assert "USD 100,000" in html
    assert "Prototype / Seed Stage" in html
    assert "0% Equity Non-Dilutive Grant" in html
    assert "94% Compatibility Match" in html

    # Dual CTAs for founder
    assert "View Grant" in html
    assert "Generate Pitch Draft" in html
    assert "View Grant Details:" in text
    assert "Generate Pitch Draft:" in text


def test_color_coded_match_score_badges():
    """Verify match score badges are green (>=80%), yellow (60-79%), or red (<60%)."""
    user = {"name": "Test User", "role": "student"}

    # High match >= 80% (Green)
    r_high = email_template_service.render_email_alert(user, "new_match", {"opportunity_name": "High Opp", "match_score": 95})
    assert "#065F46" in r_high["html"]
    assert "#ECFDF5" in r_high["html"]
    assert "95% Compatibility Match" in r_high["html"]

    # Medium match 60-79% (Yellow)
    r_med = email_template_service.render_email_alert(user, "new_match", {"opportunity_name": "Med Opp", "match_score": 72})
    assert "#92400E" in r_med["html"]
    assert "#FFFBEB" in r_med["html"]
    assert "72% Moderate Match" in r_med["html"]

    # Low match < 60% (Red)
    r_low = email_template_service.render_email_alert(user, "new_match", {"opportunity_name": "Low Opp", "match_score": 55})
    assert "#991B1B" in r_low["html"]
    assert "#FEF2F2" in r_low["html"]
    assert "55% Match" in r_low["html"]


def test_missing_optional_values_graceful_omission():
    """Verify that missing optional values are omitted cleanly and 'None' is never rendered."""
    user = {"name": "Test User", "role": "founder"}
    # Intentionally omit amount, funder, country, stage_fit, days_left
    opp = {
        "opportunity_name": "Mystery Grant",
        "match_score": 88,
        "amount": None,
        "funder": None,
        "country": None,
        "stage_fit": None,
        "equity_type": None
    }

    res = email_template_service.render_email_alert(user, "new_match", opp)
    html = res["html"]
    text = res["text"]

    assert "None" not in html
    assert "Unknown" not in html
    assert "None" not in text
    assert "Mystery Grant" in html


def test_weekly_digest_additional_matches_rendering():
    """Verify weekly digest renders the secondary list of top opportunities."""
    user = {"name": "Scholar Applicant", "role": "student"}
    opps = [
        {"opportunity_name": "Top Scholarship 1", "amount": "Fully Funded", "deadline": "2026-12-01", "match_score": 98},
        {"opportunity_name": "Secondary Match 2", "amount": "$30,000", "deadline": "2026-11-15", "match_score": 89},
        {"opportunity_name": "Secondary Match 3", "amount": "Tuition Waiver", "deadline": "2026-10-31", "match_score": 85}
    ]

    res = email_template_service.render_email_alert(user, "weekly_digest", opps[0], opportunities_list=opps)
    html = res["html"]

    assert "Top Scholarship 1" in html
    assert "Secondary Match 2" in html
    assert "Secondary Match 3" in html
    assert "Additional Top Matches This Week" in html


def test_dev_email_preview_route_all_combinations():
    """Verify the /dev/email-preview interactive preview route for all 6 variations."""
    combinations = [
        ("student", "new_match"),
        ("student", "deadline_approaching"),
        ("student", "weekly_digest"),
        ("founder", "new_match"),
        ("founder", "deadline_approaching"),
        ("founder", "weekly_digest")
    ]

    for role, alert_type in combinations:
        # 1. Interactive HTML view
        res = client.get(f"/dev/email-preview?role={role}&alert_type={alert_type}")
        assert res.status_code == 200
        assert "GrantFinder" in res.text
        assert "Email Template Testing Console" in res.text

        # 2. Raw email view
        raw_res = client.get(f"/dev/email-preview?role={role}&alert_type={alert_type}&format=raw")
        assert raw_res.status_code == 200
        assert "<!DOCTYPE html" in raw_res.text
        assert "GrantFinder" in raw_res.text

        # 3. Plain text view
        txt_res = client.get(f"/dev/email-preview?role={role}&alert_type={alert_type}&format=text")
        assert txt_res.status_code == 200
        assert "GRANTFINDER AI" in txt_res.text
        assert "Unsubscribe from email alerts:" in txt_res.text


def test_notify_user_freemium_and_verification_rules():
    """Verify that alerts are sent via email ONLY to verified, double-opted-in, premium subscribers."""
    unique_suffix = uuid.uuid4().hex[:8]

    # 1. Free user with double opt-in -> in_app: True, email: False
    free_email = f"free_{unique_suffix}@example.com"
    free_user = supabase_service.create_user(
        name=f"Free User {unique_suffix}",
        email=free_email,
        password_hash="pwd123",
        role="student",
        plan="free",
        email_verified=True
    )
    supabase_service.set_email_subscription(free_user["id"], True)

    free_res = notify_user(
        user_id=free_user["id"],
        message="New Erasmus Mundus opportunity match found.",
        event_type="new_match",
        title="Scholarship Alert"
    )
    assert free_res["in_app"] is True
    assert free_res["email"] is False, "Free user must not receive email alerts (in-app only)"

    # 2. Premium user WITHOUT email double opt-in -> in_app: True, email: False
    prem_unsub_email = f"premunsub_{unique_suffix}@example.com"
    prem_unsub = supabase_service.create_user(
        name=f"Premium Unsub {unique_suffix}",
        email=prem_unsub_email,
        password_hash="pwd123",
        role="founder",
        plan="premium",
        email_verified=True
    )
    supabase_service.set_email_subscription(prem_unsub["id"], False)

    unsub_res = notify_user(
        user_id=prem_unsub["id"],
        message="New Ignite grant deadline.",
        event_type="deadline_approaching",
        title="Funding Deadline"
    )
    assert unsub_res["in_app"] is True
    assert unsub_res["email"] is False, "Unsubscribed user must not receive email alerts"

    # 3. Premium verified user WITH double opt-in -> in_app: True, email: True
    prem_sub_email = f"premsub_{unique_suffix}@example.com"
    prem_sub = supabase_service.create_user(
        name=f"Premium Sub {unique_suffix}",
        email=prem_sub_email,
        password_hash="pwd123",
        role="founder",
        plan="premium",
        email_verified=True
    )
    supabase_service.set_user_verified(prem_sub["id"], True)
    supabase_service.set_email_subscription(prem_sub["id"], True)

    sub_res = notify_user(
        user_id=prem_sub["id"],
        message="High-affinity startup grant discovered for your AgriTech venture.",
        event_type="new_match",
        title="Startup Grant Opportunity",
        opportunity_data={
            "opportunity_name": "AgriTech Innovation Challenge",
            "funder": "Gates Foundation",
            "amount": "USD 100,000",
            "match_score": 95
        }
    )
    assert sub_res["in_app"] is True
    assert sub_res["email"] is True, "Verified premium subscriber must receive email alert"

    # Verify notification record was written to notifications table with channel='email'
    notifs = supabase_service.get_user_notifications(prem_sub["id"])
    channels = [n.get("channel") for n in notifs]
    assert "email" in channels
    assert "in_app" in channels


def test_unsubscribe_endpoint_deactivates_subscription():
    """Verify that clicking the unsubscribe link generated in emails sets email_subscribed = False."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"unsub_test_{unique_suffix}@example.com"
    user = supabase_service.create_user(
        name=f"Subscriber {unique_suffix}",
        email=email,
        password_hash="pwd123",
        role="student",
        plan="premium",
        email_verified=True
    )
    supabase_service.set_email_subscription(user["id"], True)
    assert supabase_service.is_email_subscribed(user["id"]) is True

    # Generate unsubscribe token as done in email templates
    token = supabase_service.generate_subscription_token(user["id"], email, action="unsubscribe")

    # Visit the unsubscribe link
    unsub_res = client.get(f"/api/notifications/unsubscribe?token={token}")
    assert unsub_res.status_code == 200
    assert "Unsubscribed Successfully" in unsub_res.text

    # Verify subscription status is now False
    assert supabase_service.is_email_subscribed(user["id"]) is False
