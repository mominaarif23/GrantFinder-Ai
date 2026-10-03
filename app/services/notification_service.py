import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List
from app.config import settings
from app.services.supabase_service import supabase_service

# ==============================================================================
# Low-Level Dispatch Functions
# ==============================================================================

def send_smtp_email(recipient_email: str, subject: str, message: str) -> bool:
    """Send email via SMTP if credentials are configured."""
    if not recipient_email or not settings.SMTP_USER or not settings.SMTP_PASS:
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[GrantFinder AI] {subject}"
        msg["From"] = settings.NOTIFICATION_EMAIL_FROM
        msg["To"] = recipient_email

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
                    <h2 style="color: #0f172a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px;">GrantFinder AI Alert</h2>
                    <h3 style="color: #1e293b;">{subject}</h3>
                    <p>{message}</p>
                    <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                    <p style="font-size: 12px; color: #64748b;">This notification was dispatched automatically from your GrantFinder AI account.</p>
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

def notify_user(
    user_id: str,
    message: str,
    event_type: str = "general",
    title: Optional[str] = None
) -> Dict[str, Any]:
    """Central unified notification function as specified in Supabase Integration Plan:
    1. in_app: Always created in public.notifications for all users.
    2. email: Sent via SMTP and stored in public.notifications for all users.
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

    # 2. Email notification - always sent, all users
    if user and user.get("email"):
        send_smtp_email(user["email"], subject, message)
        try:
            supabase_service.insert_notification(user_id=user_id, message=message, channel="email")
            results["email"] = True
        except Exception:
            pass

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
