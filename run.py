"""Application entry point."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from same directory as run.py (project root) before any app code
load_dotenv(Path(__file__).resolve().parent / ".env")

# Print .env-derived Adyen vars (mask secrets)
print("Loaded .env (Adyen):")
def _mask(s, show=4):
    return (s[:show] + "..." + s[-show:]) if s and len(s) > show * 2 else ("(empty)" if not s else "***")
for _k in ("ADYEN_API_KEY", "ADYEN_CLIENT_KEY", "ADYEN_MERCHANT_ACCOUNT", "ADYEN_ENVIRONMENT"):
    _v = os.environ.get(_k, "")
    if "KEY" in _k:
        print(f"  {_k}={_mask(_v)} (len={len(_v)})")
    else:
        print(f"  {_k}={_v or '(empty)'}")

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", True))
