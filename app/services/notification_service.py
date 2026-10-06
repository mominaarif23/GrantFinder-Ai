import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List
from app.config import settings
from app.services.supabase_service import supabase_service

# ==============================================================================
# Low-Level Dispatch Functions
# ==============================================================================

def send_smtp_email(
    recipient_email: str,
    subject: str,
    message: str,
    unsubscribe_url: Optional[str] = None,
    action_url: Optional[str] = None,
    action_label: Optional[str] = None,
    otp_code: Optional[str] = None
) -> bool:
    """Send email via SMTP if credentials are configured, with simulated dummy-domain bounce guard."""
    if not recipient_email:
        return True

    # Guard against sending actual SMTP traffic to dummy/testing domains to prevent bounces
    dummy_domains = ("@grantfinder.ai", "@example.com", "@test.com", "@localhost")
    if any(recipient_email.lower().endswith(d) for d in dummy_domains):
        return True

    if not settings.SMTP_USER or not settings.SMTP_PASS:
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[GrantFinder AI] {subject}"
        msg["From"] = settings.NOTIFICATION_EMAIL_FROM
        msg["To"] = recipient_email

        otp_block_html = ""
        if otp_code:
            formatted_otp = f"{otp_code[:3]} {otp_code[3:]}" if len(otp_code) == 6 else otp_code
            otp_block_html = f"""
            <div style="margin: 28px 0; text-align: center; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 22px;">
                <span style="font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.5px; color: #475569; display: block; margin-bottom: 10px;">
                    Your 6-Digit Verification Code
                </span>
                <div style="display: inline-block; background-color: #0f172a; color: #38bdf8; font-size: 32px; font-weight: 800; letter-spacing: 8px; padding: 14px 32px; border-radius: 12px; font-family: 'SF Mono', 'Courier New', monospace; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                    {formatted_otp}
                </div>
                <p style="font-size: 11px; color: #64748b; margin: 10px 0 0 0;">
                    Code is valid for 15 minutes. Never share this code with anyone.
                </p>
            </div>
            """

        action_btn_html = ""
        if action_url and action_label:
            action_btn_html = f"""
            <div style="margin: 24px 0; text-align: center;">
                <a href="{action_url}" style="background-color: #1d4ed8; color: #ffffff; padding: 14px 28px; font-weight: 700; font-size: 13px; text-decoration: none; border-radius: 10px; display: inline-block; box-shadow: 0 4px 10px rgba(29, 78, 216, 0.25);">
                    {action_label} &rarr;
                </a>
            </div>
            """

        unsub_html = ""
        if unsubscribe_url:
            unsub_html = f"""
            <p style="font-size: 11px; color: #94a3b8; margin-top: 15px; line-height: 1.5;">
                You are receiving this official alert because your email was registered on GrantFinder AI.
                <br>
                <a href="{unsubscribe_url}" style="color: #64748b; text-decoration: underline;">Unsubscribe from notification alerts</a>
            </p>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f1f5f9; padding: 24px 12px; margin: 0;">
                <div style="max-width: 580px; margin: 0 auto; background: #ffffff; padding: 32px; border: 1px solid #e2e8f0; border-radius: 18px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);">
                    <!-- Header -->
                    <div style="border-bottom: 1px solid #f1f5f9; padding-bottom: 20px; margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <span style="font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px;">GrantFinder <span style="color: #2563eb;">AI</span></span>
                            <span style="display: block; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #94a3b8; margin-top: 2px;">Intelligent Funding Discovery</span>
                        </div>
                        <span style="display: inline-block; font-size: 10px; font-weight: 700; background-color: #eff6ff; color: #1d4ed8; padding: 4px 10px; border-radius: 9999px; border: 1px solid #bfdbfe;">
                            Verified Academic Portal
                        </span>
                    </div>

                    <!-- Main Subject & Body -->
                    <h2 style="color: #0f172a; font-size: 18px; font-weight: 800; margin: 0 0 14px 0; letter-spacing: -0.3px;">
                        {subject}
                    </h2>
                    <div style="color: #334155; font-size: 13.5px; line-height: 1.65;">
                        {message}
                    </div>

                    {otp_block_html}

                    {action_btn_html}

                    <!-- Footer -->
                    <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 28px 0 18px 0;">
                    {unsub_html}
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 12px;">
                        &copy; 2026 GrantFinder AI &bull; Pakistan & Global Scholarships and Innovation Grants
                    </div>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.NOTIFICATION_EMAIL_FROM, recipient_email, msg.as_string())
        return True
    except Exception:
        return False

import httpx

def send_whatsapp_message(to_number: str, message: str) -> bool:
    """Send WhatsApp message via Meta WhatsApp Cloud API or CallMeBot API.
    Zero Twilio dependency. Works in Pakistan without paid numbers or credit cards.
    """
    if not to_number or not message:
        return True

    clean_number = "".join(ch for ch in to_number if ch.isdigit())
    formatted_msg = f"*GrantFinder AI Priority Alert*\n{message}"

    # 1. Meta WhatsApp Cloud API (Official, free tier 1,000 service conversations/month)
    if settings.WHATSAPP_CLOUD_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID:
        try:
            url = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_CLOUD_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": clean_number,
                "type": "text",
                "text": {"body": formatted_msg}
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, json=payload, headers=headers)
                return res.status_code in (200, 201)
        except Exception:
            return False

    # 2. CallMeBot API (Free HTTP GET, zero setup for Pakistan)
    if settings.CALLMEBOT_API_KEY:
        try:
            url = "https://api.callmebot.com/whatsapp.php"
            params = {
                "phone": clean_number,
                "text": formatted_msg,
                "apikey": settings.CALLMEBOT_API_KEY
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, params=params)
                return res.status_code == 200
        except Exception:
            return False

    # 3. Resilient fallback / simulation mode
    return True

# Backward compatibility alias
send_twilio_whatsapp = send_whatsapp_message

# ==============================================================================
# Unified Notification Function (All 3 Channels)
# ==============================================================================

def send_optin_confirmation_email(
    user_id: str,
    recipient_email: str,
    user_name: str,
    base_url: str = ""
) -> bool:
    """Send one-time double opt-in verification email with secure 6-digit OTP code and confirmation button."""
    token = supabase_service.generate_subscription_token(user_id, recipient_email, action="confirm")
    otp_code = supabase_service.generate_email_otp(user_id, recipient_email)
    domain = base_url.rstrip('/') if base_url else "https://grantfinder-ai.onrender.com"
    confirm_url = f"{domain}/api/notifications/confirm-email?token={token}"

    subject = "Verify Your Email & Activate Scholarship Alerts"
    message = (
        f"Dear <strong>{user_name}</strong>,<br><br>"
        "Thank you for joining <strong>GrantFinder AI</strong>. To activate your student scholarship and startup grant "
        "notifications, please enter your 6-digit verification code below in your profile or click the one-click activation button."
    )
    return send_smtp_email(
        recipient_email=recipient_email,
        subject=subject,
        message=message,
        action_url=confirm_url,
        action_label="Verify & Activate Email Alerts",
        otp_code=otp_code
    )

def notify_user(
    user_id: str,
    message: str,
    event_type: str = "general",
    title: Optional[str] = None
) -> Dict[str, Any]:
    """Central unified notification function as specified in Supabase Integration Plan:
    1. in_app: Always created in public.notifications for all users.
    2. email: Sent via SMTP ONLY if double opt-in confirmed (email_subscribed == True).
    3. whatsapp: Sent via WhatsApp API and stored in public.notifications for premium users only.
    """
    user = supabase_service.get_user_by_id(user_id)
    subject = title or f"{event_type.capitalize()} Notification"
    results = {"in_app": False, "email": False, "whatsapp": False}

    # 1. In-app notification - always created, all users
    try:
        supabase_service.insert_notification(user_id=user_id, message=message, channel="in_app")
        results["in_app"] = True
    except Exception:
        pass

    # 2. Email notification - strictly gated behind double opt-in confirmation
    if user and user.get("email"):
        if supabase_service.is_email_subscribed(user_id):
            unsub_token = supabase_service.generate_subscription_token(user_id, user["email"], action="unsubscribe")
            unsub_url = f"https://grantfinder-ai.onrender.com/api/notifications/unsubscribe?token={unsub_token}"
            send_smtp_email(user["email"], subject, message, unsubscribe_url=unsub_url)
            try:
                supabase_service.insert_notification(user_id=user_id, message=message, channel="email")
                results["email"] = True
            except Exception:
                pass
        else:
            # Gated: user has not clicked confirmation link
            results["email"] = False

    # 3. WhatsApp notification - premium users only
    if user and user.get("plan") == "premium":
        phone_number = user.get("phone_number") or "+923001234567"
        send_whatsapp_message(phone_number, message)
        try:
            supabase_service.insert_notification(user_id=user_id, message=message, channel="whatsapp")
            results["whatsapp"] = True
        except Exception:
            pass

    return results

def dispatch_opportunity_alert(
    user_id: str,
    email: str,
    plan: str,
    opp_name: str,
    opp_type: str,
    deadline: str,
    match_score: int
):
    """Trigger an opportunity match alert across appropriate channels."""
    message = f"We matched you with '{opp_name}' with a {match_score}% match score. Upcoming deadline: {deadline}."
    notify_user(
        user_id=user_id,
        message=message,
        event_type="opportunity_match",
        title=f"New {opp_type.capitalize()} Match: {opp_name}"
    )

def send_in_app_notification(user_id: str, title: str, message: str) -> Dict[str, Any]:
    formatted = f"{title}: {message}" if title else message
    return supabase_service.insert_notification(user_id=user_id, message=formatted, channel="in_app")

def send_email_notification(user_id: str, recipient_email: str, title: str, message: str) -> bool:
    formatted = f"{title}: {message}" if title else message
    send_smtp_email(recipient_email, title, message)
    supabase_service.insert_notification(user_id=user_id, message=formatted, channel="email")
    return True

def send_whatsapp_notification(user_id: str, to_number: str, message: str) -> bool:
    send_whatsapp_message(to_number, message)
    supabase_service.insert_notification(user_id=user_id, message=message, channel="whatsapp")
    return True
