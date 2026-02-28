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
