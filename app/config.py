"""Application configuration."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root; run.py also loads it before importing app
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class DefaultConfig:
    """Default configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    HANA_PASSWORD = os.environ.get("HANA_PASSWORD", "")

    # Adyen (use test credentials; set in .env for production)
    ADYEN_API_KEY = os.environ.get("ADYEN_API_KEY", "")
    ADYEN_CLIENT_KEY = os.environ.get("ADYEN_CLIENT_KEY", "")
    ADYEN_MERCHANT_ACCOUNT = os.environ.get("ADYEN_MERCHANT_ACCOUNT", "")
    ADYEN_ENVIRONMENT = os.environ.get("ADYEN_ENVIRONMENT", "test")  # test or live
    HMAC_SECRET = os.environ.get("HMAC_SECRET", "")  # Webhook HMAC key from Customer Area

    # Xendit (Payment Sessions / Components)
    XENDIT_SECRET_KEY = os.environ.get("XENDIT_SECRET_KEY", "")
    XENDIT_PUBLIC_KEY = os.environ.get("XENDIT_PUBLIC_KEY", "")
    # Thailand mobile banking / direct debit: business ID from Xendit Dashboard (Settings → Business)
    XENDIT_DESTINATION_ACCOUNT_ID = os.environ.get("XENDIT_DESTINATION_ACCOUNT_ID", "")
