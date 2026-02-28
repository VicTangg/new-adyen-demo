"""API blueprint — JSON endpoints."""
import copy
import json
import time
import uuid
from flask import Blueprint, jsonify, request, current_app

api_bp = Blueprint("api", __name__)

# In-memory store for Adyen API logs (bounded); do not log full card/encrypted data
ADYEN_API_LOGS = []
ADYEN_API_LOGS_MAX = 50
SENSITIVE_KEYS = frozenset({"encryptedCardNumber", "encryptedSecurityCode", "encryptedExpiryMonth", "encryptedExpiryYear", "encryptedPassword", "cvc", "number"})  # redact in paymentMethod


def _sanitize(obj):
    """Return a deep copy with sensitive payment fields redacted for logging."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [_sanitize(x) for x in obj]
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key_lower = k.lower() if isinstance(k, str) else k
            if key_lower in SENSITIVE_KEYS or (isinstance(k, str) and "encrypted" in k.lower()):
                out[k] = "[REDACTED]"
            else:
                out[k] = _sanitize(v)
        return out
    return obj


def _append_adyen_log(endpoint, request_payload, response_payload, error=None):
    entry = {
        "id": str(uuid.uuid4())[:8],
        "ts": round(time.time() * 1000),
        "endpoint": endpoint,
        "request": _sanitize(copy.deepcopy(request_payload)) if request_payload else None,
        "response": response_payload,
        "error": str(error) if error else None,
    }
    ADYEN_API_LOGS.append(entry)
    while len(ADYEN_API_LOGS) > ADYEN_API_LOGS_MAX:
        ADYEN_API_LOGS.pop(0)


def get_adyen_client():
    """Return configured Adyen checkout client."""
    from Adyen import Adyen
    adyen = Adyen()
    adyen.client.xapikey = current_app.config["ADYEN_API_KEY"]
    adyen.client.platform = current_app.config["ADYEN_ENVIRONMENT"]
    adyen.client.merchant_account = current_app.config["ADYEN_MERCHANT_ACCOUNT"]
    return adyen


@api_bp.route("/health", methods=["GET"])
def health():
    """Health check for load balancers and monitoring."""
    return jsonify({"status": "ok", "service": "flask-jinja2-app"})


@api_bp.route("/items", methods=["GET"])
def list_items():
    """Example API: list items."""
    items = [
        {"id": 1, "name": "Item Alpha", "description": "First sample item"},
        {"id": 2, "name": "Item Beta", "description": "Second sample item"},
        {"id": 3, "name": "Item Gamma", "description": "Third sample item"},
    ]
    return jsonify({"items": items, "count": len(items)})


# ——— Adyen Checkout (Advanced flow) ———

@api_bp.route("/adyen/paymentMethods", methods=["POST"])
def adyen_payment_methods():
    """Fetch available payment methods from Adyen (amount, currency, countryCode)."""
    data = request.get_json() or {}
    amount = data.get("amount") or {}
    value = int(amount.get("value", 0))
    currency = amount.get("currency", "EUR")
    country_code = data.get("countryCode", "NL")
    channel = data.get("channel", "Web")
    browser_info = data.get("browserInfo")

    if not current_app.config.get("ADYEN_MERCHANT_ACCOUNT") or not current_app.config.get("ADYEN_API_KEY"):
        return jsonify({"error": "Adyen not configured"}), 503

    adyen = get_adyen_client()
    params = {
        "merchantAccount": current_app.config["ADYEN_MERCHANT_ACCOUNT"],
        "amount": {"value": value, "currency": currency},
        "countryCode": country_code,
        "channel": channel,
    }
    if browser_info:
        params["browserInfo"] = browser_info

    try:
        result = adyen.checkout.payments_api.payment_methods(params)
        resp = json.loads(result.raw_response)
        _append_adyen_log("POST /paymentMethods", params, resp, error=None)
        return jsonify(resp)
    except Exception as e:
        _append_adyen_log("POST /paymentMethods", params, None, error=e)
        err_msg = str(e)
        if "901" in err_msg or "Invalid Merchant Account" in err_msg or "AdyenAPIInvalidPermission" in type(e).__name__:
            return jsonify({
                "error": "Invalid Merchant Account. Check ADYEN_MERCHANT_ACCOUNT in .env matches your Adyen Customer Area (Account → Merchant accounts)."
            }), 400
        current_app.logger.exception("Adyen paymentMethods error")
        return jsonify({"error": err_msg}), 502


@api_bp.route("/adyen/payments", methods=["POST"])
def adyen_payments():
    """Submit payment (Drop-in payload). Supports redirect and native 3DS. Forwards full body including paymentMethod.holderName (cardholder name) to Adyen."""
    data = request.get_json() or {}
    if not current_app.config.get("ADYEN_MERCHANT_ACCOUNT") or not current_app.config.get("ADYEN_API_KEY"):
        return jsonify({"error": "Adyen not configured"}), 503

    # Ensure server-side required fields (amount, reference, returnUrl, merchantAccount)
    if "amount" not in data and "value" not in data.get("amount", {}):
        return jsonify({"error": "amount required"}), 400
    if "reference" not in data:
        data["reference"] = f"ref-{uuid.uuid4().hex[:16]}"
    if "returnUrl" not in data:
        base = request.url_root.rstrip("/")
        data["returnUrl"] = f"{base}/checkout/return"
    if "merchantAccount" not in data:
        data["merchantAccount"] = current_app.config["ADYEN_MERCHANT_ACCOUNT"]
    if "channel" not in data:
        data["channel"] = "Web"

    adyen = get_adyen_client()
    try:
        result = adyen.checkout.payments_api.payments(data)
        resp = json.loads(result.raw_response)
        _append_adyen_log("POST /payments", data, resp, error=None)
        return jsonify(resp)
    except Exception as e:
        _append_adyen_log("POST /payments", data, None, error=e)
        current_app.logger.exception("Adyen payments error")
        return jsonify({"error": str(e)}), 502


@api_bp.route("/adyen/payments/details", methods=["POST"])
def adyen_payments_details():
    """Submit payment details (e.g. after 3DS redirect or challenge)."""
    data = request.get_json() or {}
    if not data.get("details") and not data.get("paymentData"):
        return jsonify({"error": "details or paymentData required"}), 400
    if not current_app.config.get("ADYEN_MERCHANT_ACCOUNT") or not current_app.config.get("ADYEN_API_KEY"):
        return jsonify({"error": "Adyen not configured"}), 503

    adyen = get_adyen_client()
    try:
        result = adyen.checkout.payments_api.payments_details(data)
        resp = json.loads(result.raw_response)
        _append_adyen_log("POST /payments/details", data, resp, error=None)
        return jsonify(resp)
    except Exception as e:
        _append_adyen_log("POST /payments/details", data, None, error=e)
        current_app.logger.exception("Adyen payments/details error")
        return jsonify({"error": str(e)}), 502


@api_bp.route("/adyen/logs", methods=["GET"])
def adyen_logs():
    """Return recent server-side Adyen API request/response logs (for dev UI)."""
    return jsonify({"logs": list(ADYEN_API_LOGS)})
