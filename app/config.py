"""Application configuration."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root; run.py also loads it before importing app
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class DefaultConfig:
    """Default configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"

    # Adyen (use test credentials; set in .env for production)
    ADYEN_API_KEY = os.environ.get("ADYEN_API_KEY", "")
    ADYEN_CLIENT_KEY = os.environ.get("ADYEN_CLIENT_KEY", "")
    ADYEN_MERCHANT_ACCOUNT = os.environ.get("ADYEN_MERCHANT_ACCOUNT", "")
    ADYEN_ENVIRONMENT = os.environ.get("ADYEN_ENVIRONMENT", "test")  # test or live
    HMAC_SECRET = os.environ.get("HMAC_SECRET", "")  # Webhook HMAC key from Customer Area
    ADYEN_MANAGEMENT_WRITE_TOKEN = os.environ.get("ADYEN_MANAGEMENT_WRITE_TOKEN", "")

    # Xendit (Payment Sessions / Components)
    XENDIT_SECRET_KEY = os.environ.get("XENDIT_SECRET_KEY", "")
    XENDIT_PUBLIC_KEY = os.environ.get("XENDIT_PUBLIC_KEY", "")
    XENDIT_COMPONENTS_CURRENCY = os.environ.get("XENDIT_COMPONENTS_CURRENCY", "IDR")
    XENDIT_COMPONENTS_COUNTRY = os.environ.get("XENDIT_COMPONENTS_COUNTRY", "ID")
    XENDIT_ALLOWED_ORIGINS = os.environ.get("XENDIT_ALLOWED_ORIGINS", "")
    # Thailand mobile banking / direct debit: business ID from Xendit Dashboard (Settings → Business)
    XENDIT_DESTINATION_ACCOUNT_ID = os.environ.get("XENDIT_DESTINATION_ACCOUNT_ID", "")

    # Public URL used for payment redirects/origin allowlists when the request host is not canonical.
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "")

    # Image host
    IMAGE_HOST_DELETE_TOKEN = os.environ.get("IMAGE_HOST_DELETE_TOKEN", "")
