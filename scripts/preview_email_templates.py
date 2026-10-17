"""
Standalone Preview & Verification Script for GrantFinder AI Email Templates.
Renders all 6 role and alert type combinations to disk for visual and QA verification:
1. Student - New Match Found
2. Student - Deadline Approaching (7 Days Left)
3. Student - Weekly Scholarship Digest
4. Founder - New Match Found
5. Founder - Deadline Approaching (7 Days Left)
6. Founder - Weekly Startup Grant Digest

Usage:
  python scripts/preview_email_templates.py
"""

import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.services.email_template_service import email_template_service

def generate_previews():
    output_dir = os.path.join(PROJECT_ROOT, "dev_previews")
    os.makedirs(output_dir, exist_ok=True)

    test_matrix = [
        ("student", "new_match", "student_new_match"),
        ("student", "deadline_approaching", "student_deadline_7d"),
        ("student", "weekly_digest", "student_weekly_digest"),
        ("founder", "new_match", "founder_new_match"),
        ("founder", "deadline_approaching", "founder_deadline_7d"),
        ("founder", "weekly_digest", "founder_weekly_digest"),
    ]

    print("=" * 70)
    print("GrantFinder AI - Email Template Render Engine Test")
    print("=" * 70)

    for role, alert_type, filename in test_matrix:
        if role == "founder":
            user = {
                "id": "qa-founder-001",
                "name": "Hamza Tariq",
                "email": "hamza.founder@grantfinder.ai",
                "role": "founder",
                "plan": "premium"
            }
            profile = {
                "profile_type": "startup",
                "type": "startup",
                "major_or_domain": "AgriTech",
                "degree_level_stage": "Early Prototype / MVP"
            }
            opp = {
                "opportunity_name": "Global AgriTech Climate Innovation Challenge",
                "funder": "Bill & Melinda Gates Foundation & CGIAR",
                "amount": "USD 100,000",
                "stage_fit": "Prototype / MVP Launched",
                "equity_type": "0% Equity Non-Dilutive Grant",
                "country": "Pakistan & Global",
                "deadline": "December 15, 2026",
                "days_left": 7 if alert_type == "deadline_approaching" else 59,
                "match_score": 95,
                "match_reason": "Targeted specifically at climate-resilient agricultural technology startups with field pilot data."
            }
        else:
            user = {
                "id": "qa-student-001",
                "name": "Momina Tariq",
                "email": "momina.student@grantfinder.ai",
                "role": "student",
                "plan": "premium"
            }
            profile = {
                "profile_type": "academic",
                "type": "academic",
                "major_or_domain": "Computer Science & AI",
                "degree_level_stage": "Undergraduate BS"
            }
            opp = {
                "opportunity_name": "Erasmus Mundus Joint Master Degree in AI & Data Science",
                "country": "Germany & France (EU Consortium)",
                "amount": "Fully Funded (EUR 1,400/mo + Full Tuition & Travel)",
                "degree_level": "Master of Science (MSc)",
                "cgpa_fit": "Minimum 3.50 CGPA (Your CGPA: 3.82 Aligned)",
                "deadline": "November 30, 2026",
                "days_left": 7 if alert_type == "deadline_approaching" else 44,
                "match_score": 98,
                "match_reason": "Exceptional alignment with your Computer Science coursework, data science projects, and study goals."
            }

        res = email_template_service.render_email_alert(
            user=user,
            alert_type=alert_type,
            opportunity_data=opp,
            profile=profile
        )

        html_path = os.path.join(output_dir, f"{filename}.html")
        txt_path = os.path.join(output_dir, f"{filename}.txt")

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(res["html"])

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(res["text"])

        print(f"[OK] {role.upper():<7} | {alert_type:<20} | HTML: {len(res['html']):>5} bytes | TXT: {len(res['text']):>5} bytes")
        print(f"     Subject: {res['subject']}")

    print("=" * 70)
    print(f"Generated 6 preview HTML and TXT files in: {output_dir}")
    print("=" * 70)

if __name__ == "__main__":
    generate_previews()
