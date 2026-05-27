"""Application configuration."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root; run.py also loads it before importing app
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def _env_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class DefaultConfig:
    """Default configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"
    MAX_CONTENT_LENGTH = _env_int("MAX_CONTENT_LENGTH", 100 * 1024 * 1024)

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
    XENDIT_ALLOWED_ORIGINS = os.environ.get("XENDIT_ALLOWED_ORIGINS", "")
    XENDIT_SESSION_COUNTRY = os.environ.get("XENDIT_SESSION_COUNTRY", "ID")
    XENDIT_SESSION_CURRENCY = os.environ.get("XENDIT_SESSION_CURRENCY", "IDR")

    # Temporary image hosting
    IMAGE_HOST_MAX_BYTES = _env_int("IMAGE_HOST_MAX_BYTES", 100 * 1024 * 1024)
    IMAGE_HOST_DELETE_TOKEN = os.environ.get("IMAGE_HOST_DELETE_TOKEN", "")
