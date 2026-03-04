"""API blueprint — JSON endpoints."""
import copy
import json
import time
import uuid
import requests
from flask import Blueprint, jsonify, request, current_app

api_bp = Blueprint("api", __name__)

# In-memory store for Adyen API logs (bounded); do not log full card/encrypted data
ADYEN_API_LOGS = []
ADYEN_API_LOGS_MAX = 50

# In-memory store for received webhook events (bounded)
ADYEN_WEBHOOK_LOGS = []
ADYEN_WEBHOOK_LOGS_MAX = 100

# In-memory store for Xendit API logs (bounded)
XENDIT_API_LOGS = []
XENDIT_API_LOGS_MAX = 50
SENSITIVE_KEYS = frozenset({
    "encryptedCardNumber", "encryptedSecurityCode", "encryptedExpiryMonth", "encryptedExpiryYear",
    "encryptedPassword", "cvc", "number",
    "components_sdk_key", "componentsSdkKey",  # Xendit session key
})  # redact in paymentMethod / Xendit


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


def _append_xendit_log(endpoint, request_payload, response_payload, error=None):
    """Append Xendit API log (sanitizes sensitive fields)."""
    entry = {
        "id": str(uuid.uuid4())[:8],
        "ts": round(time.time() * 1000),
        "endpoint": endpoint,
        "request": _sanitize(copy.deepcopy(request_payload)) if request_payload else None,
        "response": _sanitize(copy.deepcopy(response_payload)) if response_payload else None,
        "error": str(error) if error else None,
    }
    XENDIT_API_LOGS.append(entry)
    while len(XENDIT_API_LOGS) > XENDIT_API_LOGS_MAX:
        XENDIT_API_LOGS.pop(0)


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


@api_bp.route("/xendit/logs", methods=["GET"])
def xendit_logs():
    """Return recent server-side Xendit API request/response logs (for dev UI)."""
    return jsonify({"logs": list(XENDIT_API_LOGS)})


def _append_webhook_log(payload, valid, error=None):
    """Append a webhook event to the in-memory store."""
    entry = {
        "id": str(uuid.uuid4())[:8],
        "ts": round(time.time() * 1000),
        "payload": _sanitize(copy.deepcopy(payload)) if payload else None,
        "valid": valid,
        "error": str(error) if error else None,
    }
    ADYEN_WEBHOOK_LOGS.append(entry)
    while len(ADYEN_WEBHOOK_LOGS) > ADYEN_WEBHOOK_LOGS_MAX:
        ADYEN_WEBHOOK_LOGS.pop(0)


@api_bp.route("/adyen/webhooks", methods=["POST"])
def adyen_webhooks():
    """Accept Adyen Standard webhooks. Verify HMAC signature; only accept and store if valid."""
    hmac_key = current_app.config.get("HMAC_SECRET", "").strip()
    if not hmac_key:
        current_app.logger.warning("HMAC_SECRET not configured; rejecting webhook")
        return jsonify({"error": "Webhook not configured"}), 503

    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    if not payload:
        return jsonify({"error": "Empty body"}), 400

    notification_items = payload.get("notificationItems") or []
    if not notification_items:
        return jsonify({"error": "No notificationItems"}), 400

    from Adyen.util import is_valid_hmac_notification

    for item in notification_items:
        try:
            notification = item.get("NotificationRequestItem") or item
        except (TypeError, AttributeError):
            notification = item
        if not isinstance(notification, dict):
            return jsonify({"error": "Invalid notification structure"}), 400
        if not notification.get("additionalData", {}).get("hmacSignature"):
            return jsonify({"error": "Missing hmacSignature"}), 400
        try:
            if not is_valid_hmac_notification(notification, hmac_key):
                return jsonify({"error": "HMAC signature invalid"}), 401
        except Exception as e:
            return jsonify({"error": f"HMAC verification failed: {e}"}), 401

    _append_webhook_log(payload, valid=True)
    return "accepted", 200


@api_bp.route("/adyen/webhooks/logs", methods=["GET"])
def adyen_webhook_logs():
    """Return webhook events (for dev UI)."""
    return jsonify({"logs": list(ADYEN_WEBHOOK_LOGS)})


@api_bp.route("/adyen/stores", methods=["GET"])
def adyen_stores():
    """Fetch stores from Adyen Management API for the merchant account."""
    merchant_id = current_app.config.get("ADYEN_MERCHANT_ACCOUNT")
    api_key = current_app.config.get("ADYEN_API_KEY")
    env = current_app.config.get("ADYEN_ENVIRONMENT", "test")
    if not merchant_id or not api_key:
        return jsonify({"error": "Adyen not configured"}), 503

    base = "https://management-live.adyen.com" if env == "live" else "https://management-test.adyen.com"
    url = f"{base}/v3/merchants/{merchant_id}/stores"
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    req_payload = {"merchantId": merchant_id, "endpoint": f"GET /merchants/{merchant_id}/stores"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json() if r.text else {}
        if not r.ok:
            err_resp = {"error": data.get("detail", data.get("title", r.text)), "status": r.status_code}
            _append_adyen_log("GET /merchants/{merchantId}/stores (Management)", req_payload, None, error=err_resp.get("error"))
            return jsonify(err_resp), r.status_code
        stores = data.get("data", [])
        out = [
            {"id": s.get("id"), "reference": s.get("reference"), "description": s.get("description", s.get("reference", ""))}
            for s in stores
            if s.get("reference")
        ]
        resp_payload = {"stores": out, "itemsTotal": data.get("itemsTotal"), "pagesTotal": data.get("pagesTotal")}
        _append_adyen_log("GET /merchants/{merchantId}/stores (Management)", req_payload, resp_payload, error=None)
        return jsonify({"stores": out})
    except requests.RequestException as e:
        _append_adyen_log("GET /merchants/{merchantId}/stores (Management)", req_payload, None, error=e)
        current_app.logger.exception("Adyen stores error")
        return jsonify({"error": str(e)}), 502


@api_bp.route("/adyen/stores/<store_id>", methods=["GET"])
def adyen_store_detail(store_id):
    """Fetch a single store's details from Adyen Management API."""
    merchant_id = current_app.config.get("ADYEN_MERCHANT_ACCOUNT")
    api_key = current_app.config.get("ADYEN_API_KEY")
    env = current_app.config.get("ADYEN_ENVIRONMENT", "test")
    if not merchant_id or not api_key:
        return jsonify({"error": "Adyen not configured"}), 503

    base = "https://management-live.adyen.com" if env == "live" else "https://management-test.adyen.com"
    url = f"{base}/v3/merchants/{merchant_id}/stores/{store_id}"
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    req_payload = {"merchantId": merchant_id, "storeId": store_id, "endpoint": f"GET /merchants/{merchant_id}/stores/{store_id}"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json() if r.text else {}
        if not r.ok:
            err_resp = {"error": data.get("detail", data.get("title", r.text)), "status": r.status_code}
            _append_adyen_log("GET /merchants/{merchantId}/stores/{storeId} (Management)", req_payload, None, error=err_resp.get("error"))
            return jsonify(err_resp), r.status_code
        _append_adyen_log("GET /merchants/{merchantId}/stores/{storeId} (Management)", req_payload, data, error=None)
        return jsonify(data)
    except requests.RequestException as e:
        _append_adyen_log("GET /merchants/{merchantId}/stores/{storeId} (Management)", req_payload, None, error=e)
        current_app.logger.exception("Adyen store detail error")
        return jsonify({"error": str(e)}), 502


@api_bp.route("/adyen/stores/<store_id>", methods=["PATCH"])
def adyen_store_update(store_id):
    """Update a store via Adyen Management API PATCH /merchants/{merchantId}/stores/{storeId}."""
    merchant_id = current_app.config.get("ADYEN_MERCHANT_ACCOUNT")
    api_key = current_app.config.get("ADYEN_API_KEY")
    env = current_app.config.get("ADYEN_ENVIRONMENT", "test")
    if not merchant_id or not api_key:
        return jsonify({"error": "Adyen not configured"}), 503

    data = request.get_json() or {}
    if not data:
        return jsonify({"error": "Request body required"}), 400

    base = "https://management-live.adyen.com" if env == "live" else "https://management-test.adyen.com"
    url = f"{base}/v3/merchants/{merchant_id}/stores/{store_id}"
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    req_payload = {"merchantId": merchant_id, "storeId": store_id, "endpoint": f"PATCH /merchants/{merchant_id}/stores/{store_id}", "body": data}

    try:
        r = requests.patch(url, headers=headers, json=data, timeout=10)
        resp_data = r.json() if r.text else {}
        if not r.ok:
            err_resp = {"error": resp_data.get("detail", resp_data.get("title", r.text)), "status": r.status_code}
            _append_adyen_log("PATCH /merchants/{merchantId}/stores/{storeId} (Management)", req_payload, None, error=err_resp.get("error"))
            return jsonify(err_resp), r.status_code
        _append_adyen_log("PATCH /merchants/{merchantId}/stores/{storeId} (Management)", req_payload, resp_data, error=None)
        return jsonify(resp_data)
    except requests.RequestException as e:
        _append_adyen_log("PATCH /merchants/{merchantId}/stores/{storeId} (Management)", req_payload, None, error=e)
        current_app.logger.exception("Adyen store update error")
        return jsonify({"error": str(e)}), 502


@api_bp.route("/adyen/splitConfigurations/<split_configuration_id>", methods=["GET"])
def adyen_split_configuration(split_configuration_id):
    """Fetch split configuration profile from Adyen Management API."""
    merchant_id = current_app.config.get("ADYEN_MERCHANT_ACCOUNT")
    api_key = current_app.config.get("ADYEN_API_KEY")
    env = current_app.config.get("ADYEN_ENVIRONMENT", "test")
    if not merchant_id or not api_key:
        return jsonify({"error": "Adyen not configured"}), 503

    base = "https://management-live.adyen.com" if env == "live" else "https://management-test.adyen.com"
    url = f"{base}/v3/merchants/{merchant_id}/splitConfigurations/{split_configuration_id}"
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    req_payload = {"merchantId": merchant_id, "splitConfigurationId": split_configuration_id, "endpoint": f"GET /merchants/{merchant_id}/splitConfigurations/{split_configuration_id}"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json() if r.text else {}
        if not r.ok:
            err_resp = {"error": data.get("detail", data.get("title", r.text)), "status": r.status_code}
            _append_adyen_log("GET /merchants/{merchantId}/splitConfigurations/{splitConfigurationId} (Management)", req_payload, None, error=err_resp.get("error"))
            return jsonify(err_resp), r.status_code
        _append_adyen_log("GET /merchants/{merchantId}/splitConfigurations/{splitConfigurationId} (Management)", req_payload, data, error=None)
        return jsonify(data)
    except requests.RequestException as e:
        _append_adyen_log("GET /merchants/{merchantId}/splitConfigurations/{splitConfigurationId} (Management)", req_payload, None, error=e)
        current_app.logger.exception("Adyen split configuration error")
        return jsonify({"error": str(e)}), 502


@api_bp.route("/adyen/splitConfigurations/<split_configuration_id>/rules/<rule_id>", methods=["PATCH"])
def adyen_split_rule_update(split_configuration_id, rule_id):
    """Update split conditions via PATCH /merchants/{merchantId}/splitConfigurations/{splitConfigurationId}/rules/{ruleId}."""
    merchant_id = current_app.config.get("ADYEN_MERCHANT_ACCOUNT")
    api_key = current_app.config.get("ADYEN_API_KEY")
    env = current_app.config.get("ADYEN_ENVIRONMENT", "test")
    if not merchant_id or not api_key:
        return jsonify({"error": "Adyen not configured"}), 503

    data = request.get_json() or {}
    if not data:
        return jsonify({"error": "Request body required"}), 400

    base = "https://management-live.adyen.com" if env == "live" else "https://management-test.adyen.com"
    url = f"{base}/v3/merchants/{merchant_id}/splitConfigurations/{split_configuration_id}/rules/{rule_id}"
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    req_payload = {"merchantId": merchant_id, "splitConfigurationId": split_configuration_id, "ruleId": rule_id, "body": data}

    try:
        r = requests.patch(url, headers=headers, json=data, timeout=10)
        resp_data = r.json() if r.text else {}
        if not r.ok:
            err_resp = {"error": resp_data.get("detail", resp_data.get("title", r.text)), "status": r.status_code}
            _append_adyen_log("PATCH /merchants/{merchantId}/splitConfigurations/.../rules/{ruleId} (Management)", req_payload, None, error=err_resp.get("error"))
            return jsonify(err_resp), r.status_code
        _append_adyen_log("PATCH /merchants/{merchantId}/splitConfigurations/.../rules/{ruleId} (Management)", req_payload, resp_data, error=None)
        return jsonify(resp_data)
    except requests.RequestException as e:
        _append_adyen_log("PATCH /merchants/{merchantId}/splitConfigurations/.../rules/{ruleId} (Management)", req_payload, None, error=e)
        current_app.logger.exception("Adyen split rule update error")
        return jsonify({"error": str(e)}), 502


@api_bp.route("/adyen/splitConfigurations/<split_configuration_id>/rules/<rule_id>/splitLogic/<split_logic_id>", methods=["PATCH"])
def adyen_split_logic_update(split_configuration_id, rule_id, split_logic_id):
    """Update split logic via PATCH /merchants/{merchantId}/splitConfigurations/.../rules/{ruleId}/splitLogic/{splitLogicId}."""
    merchant_id = current_app.config.get("ADYEN_MERCHANT_ACCOUNT")
    api_key = current_app.config.get("ADYEN_API_KEY")
    env = current_app.config.get("ADYEN_ENVIRONMENT", "test")
    if not merchant_id or not api_key:
        return jsonify({"error": "Adyen not configured"}), 503

    data = request.get_json() or {}
    if not data:
        return jsonify({"error": "Request body required"}), 400

    base = "https://management-live.adyen.com" if env == "live" else "https://management-test.adyen.com"
    url = f"{base}/v3/merchants/{merchant_id}/splitConfigurations/{split_configuration_id}/rules/{rule_id}/splitLogic/{split_logic_id}"
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    req_payload = {"merchantId": merchant_id, "splitConfigurationId": split_configuration_id, "ruleId": rule_id, "splitLogicId": split_logic_id, "body": data}

    try:
        r = requests.patch(url, headers=headers, json=data, timeout=10)
        resp_data = r.json() if r.text else {}
        if not r.ok:
            err_resp = {"error": resp_data.get("detail", resp_data.get("title", r.text)), "status": r.status_code}
            _append_adyen_log("PATCH /merchants/{merchantId}/splitConfigurations/.../splitLogic/{splitLogicId} (Management)", req_payload, None, error=err_resp.get("error"))
            return jsonify(err_resp), r.status_code
        _append_adyen_log("PATCH /merchants/{merchantId}/splitConfigurations/.../splitLogic/{splitLogicId} (Management)", req_payload, resp_data, error=None)
        return jsonify(resp_data)
    except requests.RequestException as e:
        _append_adyen_log("PATCH /merchants/{merchantId}/splitConfigurations/.../splitLogic/{splitLogicId} (Management)", req_payload, None, error=e)
        current_app.logger.exception("Adyen split logic update error")
        return jsonify({"error": str(e)}), 502


# ——— Xendit Payment Sessions (Components one-time payment) ———

@api_bp.route("/xendit/sessions", methods=["POST"])
def xendit_create_session():
    """Create a Xendit Payment Session for Components (one-time payment)."""
    secret_key = current_app.config.get("XENDIT_SECRET_KEY", "").strip()
    if not secret_key:
        return jsonify({"error": "Xendit not configured"}), 503

    data = request.get_json() or {}
    amount = data.get("amount")
    currency = data.get("currency", "IDR")
    country = data.get("country", "ID")

    if amount is None:
        from app.routes.pages import get_checkout_total_cents
        amount = get_checkout_total_cents()

    ref_id = f"xendit-{uuid.uuid4().hex[:16]}"
    cust_ref = str(uuid.uuid4())

    # Xendit requires HTTPS for origins; prefer client-provided origin (handles ngrok, etc.)
    client_origin = (data.get("origin") or "").strip()
    if client_origin and not client_origin.startswith("https://"):
        client_origin = client_origin.replace("http://", "https://", 1)
    base_url = request.url_root.rstrip("/")
    base_https = base_url if base_url.startswith("https://") else base_url.replace("http://", "https://", 1)
    origins = [o for o in [client_origin, base_https, "https://localhost:5001", "https://new-adyen-demo-377583b87f3c.herokuapp.com"] if o]
    origins = list(dict.fromkeys(origins))
    payload = {
        "reference_id": ref_id,
        "session_type": "PAY",
        "mode": "COMPONENTS",
        "amount": int(amount),
        "currency": currency,
        "country": country,
        "customer": {
            "reference_id": cust_ref,
            "type": "INDIVIDUAL",
            "email": data.get("customer_email", "customer@example.com"),
            "mobile_number": data.get("customer_mobile", "+628123456789"),
            "individual_detail": {
                "given_names": data.get("customer_given_names", "John"),
                "surname": data.get("customer_surname", "Doe"),
            },
        },
        "components_configuration": {
            "origins": origins,
        },
    }

    url = "https://api.xendit.co/sessions"
    auth = (secret_key, "")
    headers = {"Content-Type": "application/json"}
    req_payload = {"url": url, "body": payload}

    try:
        r = requests.post(url, json=payload, auth=auth, headers=headers, timeout=15)
        resp = r.json() if r.text else {}
        if not r.ok:
            err_msg = resp.get("message", resp.get("error", r.text))
            _append_xendit_log("POST /sessions", req_payload, None, error=err_msg)
            return jsonify({"error": err_msg, "status": r.status_code}), r.status_code
        _append_xendit_log("POST /sessions", req_payload, resp, error=None)
        return jsonify(resp)
    except requests.RequestException as e:
        _append_xendit_log("POST /sessions", req_payload, None, error=e)
        current_app.logger.exception("Xendit session error")
        return jsonify({"error": str(e)}), 502


# Thailand channels that may require destination_account_id (BaaS account ID from baas-dashboard.xendit.co)
# BAY_GBW requires it; KRUNGSRI_MOBILE_BANKING may work without for standard accounts
XENDIT_THAILAND_DESTINATION_CHANNELS = frozenset({
    "KRUNGSRI_DIRECT_DEBIT", "BA_BBL", "BA_SCB", "BA_KTB", "BA_KBANK",
})

# Channel config: (country, currency, default_amount, requires_customer)
# Thailand Direct Debit: KRUNGSRI_DIRECT_DEBIT (confirmed), BAY_GBW_MOBILE_BANKING (Bank of Ayudhya/Krungsri)
XENDIT_CHANNEL_CONFIG = {
    "GRABPAY": ("MY", "MYR", 50, False),
    "ASTRAPAY": ("ID", "IDR", 50000, False),
    "DANA": ("ID", "IDR", 50000, False),
    "GCASH": ("PH", "PHP", 500, False),
    "KRUNGSRI_DIRECT_DEBIT": ("TH", "THB", 500, True),
    "KRUNGSRI_MOBILE_BANKING": ("TH", "THB", 500, True),  # Krungsri mobile banking (requires account_mobile_number)
    "BA_BBL": ("TH", "THB", 500, True),  # Bangkok Bank
    "BA_SCB": ("TH", "THB", 500, True),  # Siam Commercial Bank
    "BA_KTB": ("TH", "THB", 500, True),  # KrungThai Bank
    "BA_KBANK": ("TH", "THB", 500, True),  # Kasikornbank
}


def _thai_customer():
    """Customer object required by Thailand Direct Debit channels (mobile + ID validation)."""
    return {
        "type": "INDIVIDUAL",
        "reference_id": f"cust-{uuid.uuid4().hex[:12]}",
        "individual_detail": {"given_names": "John", "surname": "Doe"},
        "email": "customer@example.com",
        "mobile_number": "+66812345678",
    }


def _create_xendit_payment_request(channel_code, amount, success_url, failure_url):
    """Build payment request payload for a given channel."""
    config = XENDIT_CHANNEL_CONFIG.get(channel_code)
    if not config:
        return None, f"Unknown channel: {channel_code}"
    country, currency, default_amt, requires_customer = config
    amt = float(amount) if amount is not None else default_amt
    ref_id = f"{channel_code.lower()}-{uuid.uuid4().hex[:12]}"
    channel_props = {
        "success_return_url": success_url,
        "failure_return_url": failure_url,
    }
    if requires_customer:
        channel_props["account_mobile_number"] = "+66812345678"
        channel_props["identity_document_number"] = "1234567890123"  # Thai national ID (13 digits)
    # Thailand aggregator channels: destination_account_id must be a BaaS account ID
    # (from https://baas-dashboard.xendit.co/), NOT the regular Business ID.
    # Only send if set; omit for standard accounts (may get "required property" error).
    if channel_code in XENDIT_THAILAND_DESTINATION_CHANNELS:
        dest_id = current_app.config.get("XENDIT_DESTINATION_ACCOUNT_ID", "").strip()
        if dest_id:
            channel_props["destination_account_id"] = dest_id

    payload = {
        "reference_id": ref_id,
        "type": "PAY",
        "country": country,
        "currency": currency,
        "request_amount": amt,
        "capture_method": "AUTOMATIC",
        "channel_code": channel_code,
        "channel_properties": channel_props,
        "description": f"Payment via {channel_code}",
        "metadata": {"source": "xendit_checkout", "channel": channel_code},
    }
    if requires_customer:
        payload["customer"] = _thai_customer()
    return payload, None


def _do_xendit_payment_request(channel_code, amount, success_url, failure_url):
    """Execute Xendit payment request and return (redirect_url, error_response)."""
    secret_key = current_app.config.get("XENDIT_SECRET_KEY", "").strip()
    if not secret_key:
        return None, (jsonify({"error": "Xendit not configured"}), 503)

    payload, err = _create_xendit_payment_request(channel_code, amount, success_url, failure_url)
    if err:
        return None, (jsonify({"error": err}), 400)

    url = "https://api.xendit.co/v3/payment_requests"
    auth = (secret_key, "")
    headers = {"Content-Type": "application/json", "api-version": "2024-11-11"}
    req_payload = {"url": url, "body": payload}

    try:
        r = requests.post(url, json=payload, auth=auth, headers=headers, timeout=15)
        resp = r.json() if r.text else {}
        if not r.ok:
            err_msg = resp.get("message", resp.get("error", r.text))
            _append_xendit_log(f"POST /v3/payment_requests ({channel_code})", req_payload, None, error=err_msg)
            return None, (jsonify({"error": err_msg, "status": r.status_code}), r.status_code)

        redirect_url = None
        for action in resp.get("actions") or []:
            if action.get("type") == "REDIRECT_CUSTOMER":
                redirect_url = action.get("value")
                break

        _append_xendit_log(f"POST /v3/payment_requests ({channel_code})", req_payload, resp, error=None)

        if not redirect_url:
            return None, (jsonify({"error": "No redirect URL in response", "response": resp}), 502)

        return (redirect_url, resp.get("id")), None
    except requests.RequestException as e:
        _append_xendit_log(f"POST /v3/payment_requests ({channel_code})", req_payload, None, error=e)
        current_app.logger.exception("Xendit payment request error")
        return None, (jsonify({"error": str(e)}), 502)


@api_bp.route("/xendit/payment-request", methods=["POST"])
def xendit_payment_request():
    """Create a payment request for a given channel and return the redirect URL."""
    data = request.get_json() or {}
    channel_code = (data.get("channel_code") or "").strip().upper()
    if not channel_code:
        return jsonify({"error": "channel_code required"}), 400

    base_url = request.url_root.rstrip("/")
    success_url = data.get("success_return_url") or f"{base_url}/checkout/success"
    failure_url = data.get("failure_return_url") or f"{base_url}/checkout/failed"

    result, err = _do_xendit_payment_request(
        channel_code, data.get("amount"), success_url, failure_url
    )
    if err:
        return err[0], err[1]
    redirect_url, payment_id = result
    return jsonify({"redirect_url": redirect_url, "payment_request_id": payment_id})


@api_bp.route("/xendit/payment-grabpay", methods=["POST"])
def xendit_payment_grabpay():
    """Legacy: Create GrabPay payment. Prefer POST /xendit/payment-request with channel_code=GRABPAY."""
    data = request.get_json() or {}
    base_url = request.url_root.rstrip("/")
    success_url = data.get("success_return_url") or f"{base_url}/checkout/success"
    failure_url = data.get("failure_return_url") or f"{base_url}/checkout/failed"
    result, err = _do_xendit_payment_request("GRABPAY", data.get("amount"), success_url, failure_url)
    if err:
        return err[0], err[1]
    redirect_url, payment_id = result
    return jsonify({"redirect_url": redirect_url, "payment_request_id": payment_id})
