import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    APP_NAME: str = os.getenv("APP_NAME", "GrantFinder AI")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "grantfinder-super-secret-key-production-change-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./grantfinder.db")
    
    # External API Keys (Optional with built-in resilient mock fallbacks)
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Supabase Database & Auth
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://jxvouadenzfxicecqeri.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "sb_publishable_TmFlWjB6qeJwMMCY-NXEVQ_u2vt0j6j")
    
    # Notifications: SMTP
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    NOTIFICATION_EMAIL_FROM: str = os.getenv("NOTIFICATION_EMAIL_FROM", "noreply@grantfinder.ai")
    
    # Notifications: WhatsApp (Meta WhatsApp Cloud API or CallMeBot API - zero cost in Pakistan)
    WHATSAPP_CLOUD_TOKEN: str = os.getenv("WHATSAPP_CLOUD_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    CALLMEBOT_API_KEY: str = os.getenv("CALLMEBOT_API_KEY", "")

settings = Settings()
