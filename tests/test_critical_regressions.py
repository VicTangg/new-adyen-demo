import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.routes import api as api_module


class _AdyenResult:
    def __init__(self, payload):
        self.raw_response = json.dumps(payload)


class _AdyenPaymentsApi:
    def __init__(self):
        self.payment_methods_payload = None
        self.payments_payload = None

    def payment_methods(self, payload):
        self.payment_methods_payload = payload
        return _AdyenResult({"paymentMethods": []})

    def payments(self, payload):
        self.payments_payload = payload
        return _AdyenResult({"resultCode": "Authorised"})


class _AdyenClient:
    def __init__(self):
        self.payments_api = _AdyenPaymentsApi()
        self.checkout = self


class _HttpResponse:
    def __init__(self, payload, ok=True, status_code=200):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class CriticalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.static_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.static_dir.cleanup)
        self.app = self._make_app()
        self.client = self.app.test_client()

    def _make_app(self, **overrides):
        config = {
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_CLIENT_KEY": "adyen-client-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "management-token",
            "IMAGE_HOST_DELETE_TOKEN": "delete-token",
            "XENDIT_SECRET_KEY": "xendit-secret",
            "SERVER_NAME": "shop.example",
        }
        config.update(overrides)
        app = create_app(config)
        app.static_folder = self.static_dir.name
        return app

    def _uploads_dir(self):
        path = Path(self.static_dir.name) / api_module.IMAGE_HOST_DIR_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_image_host_list_does_not_purge_existing_files_over_quota(self):
        keep = self._uploads_dir() / "keep.png"
        keep.write_bytes(b"keep")

        with patch.object(api_module, "IMAGE_HOST_MAX_BYTES", 1):
            response = self.client.get("/api/image-host/list")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(keep.exists())
        self.assertEqual(["keep.png"], [img["filename"] for img in response.get_json()["images"]])

    def test_over_quota_image_upload_removes_only_new_file(self):
        keep = self._uploads_dir() / "keep.png"
        keep.write_bytes(b"keep")

        with patch.object(api_module, "IMAGE_HOST_MAX_BYTES", 4):
            response = self.client.post(
                "/api/image-host/upload",
                data={"image": (io.BytesIO(b"new"), "new.png", "image/png")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 507)
        self.assertTrue(keep.exists())
        self.assertEqual(["keep.png"], [path.name for path in self._uploads_dir().iterdir()])

    def test_image_delete_all_requires_token(self):
        keep = self._uploads_dir() / "keep.png"
        keep.write_bytes(b"keep")

        unauthorized = self.client.post("/api/image-host/delete-all")

        self.assertEqual(unauthorized.status_code, 401)
        self.assertTrue(keep.exists())

        authorized = self.client.post(
            "/api/image-host/delete-all",
            headers={"X-Image-Host-Delete-Token": "delete-token"},
        )

        self.assertEqual(authorized.status_code, 200)
        self.assertFalse(keep.exists())

    def test_adyen_payment_methods_uses_server_checkout_amount(self):
        adyen = _AdyenClient()

        with patch("app.routes.api.get_adyen_client", return_value=adyen):
            response = self.client.post(
                "/api/adyen/paymentMethods",
                json={
                    "amount": {"value": 1, "currency": "USD"},
                    "countryCode": "US",
                    "channel": "iOS",
                    "browserInfo": {"userAgent": "test"},
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual({"value": 9498, "currency": "EUR"}, adyen.payments_api.payment_methods_payload["amount"])
        self.assertEqual("NL", adyen.payments_api.payment_methods_payload["countryCode"])
        self.assertEqual("Web", adyen.payments_api.payment_methods_payload["channel"])

    def test_adyen_payment_uses_server_amount_and_return_url(self):
        adyen = _AdyenClient()

        with patch("app.routes.api.get_adyen_client", return_value=adyen):
            response = self.client.post(
                "/api/adyen/payments",
                json={
                    "paymentMethod": {"type": "scheme"},
                    "amount": {"value": 1, "currency": "USD"},
                    "returnUrl": "https://evil.example/return",
                    "merchantAccount": "attacker-merchant",
                    "channel": "iOS",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = adyen.payments_api.payments_payload
        self.assertEqual({"value": 9498, "currency": "EUR"}, payload["amount"])
        self.assertEqual("http://shop.example/checkout/return", payload["returnUrl"])
        self.assertEqual("merchant-account", payload["merchantAccount"])
        self.assertEqual("Web", payload["channel"])

    def test_management_patch_endpoints_require_write_token(self):
        endpoints = [
            "/api/adyen/stores/store-1",
            "/api/adyen/splitConfigurations/config-1/rules/rule-1",
            "/api/adyen/splitConfigurations/config-1/rules/rule-1/splitLogic/logic-1",
        ]

        with patch("app.routes.api.requests.patch") as patch_request:
            for endpoint in endpoints:
                response = self.client.patch(endpoint, json={"description": "changed"})
                self.assertEqual(response.status_code, 401)

        patch_request.assert_not_called()

    def test_xendit_session_uses_server_amount_and_origins(self):
        captured = []

        def fake_post(url, json, auth, headers, timeout):
            captured.append(json)
            return _HttpResponse({"components_sdk_key": "sdk-key"})

        with patch("app.routes.api.requests.post", side_effect=fake_post):
            response = self.client.post(
                "/api/xendit/sessions",
                json={
                    "amount": 1,
                    "currency": "USD",
                    "country": "US",
                    "origin": "https://evil.example",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = captured[0]
        self.assertEqual(9498, payload["amount"])
        self.assertEqual("IDR", payload["currency"])
        self.assertEqual("ID", payload["country"])
        self.assertIn("https://shop.example", payload["components_configuration"]["origins"])
        self.assertNotIn("https://evil.example", payload["components_configuration"]["origins"])

    def test_xendit_payment_request_uses_channel_defaults_and_server_return_urls(self):
        captured = []

        def fake_post(url, json, auth, headers, timeout):
            captured.append(json)
            return _HttpResponse({
                "id": "payment-request-id",
                "actions": [{"type": "REDIRECT_CUSTOMER", "value": "https://xendit.example/redirect"}],
            })

        with patch("app.routes.api.requests.post", side_effect=fake_post):
            response = self.client.post(
                "/api/xendit/payment-request",
                json={
                    "channel_code": "GRABPAY",
                    "amount": 1,
                    "success_return_url": "https://evil.example/success",
                    "failure_return_url": "https://evil.example/failure",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = captured[0]
        self.assertEqual(50, payload["request_amount"])
        self.assertEqual("http://shop.example/checkout/success", payload["channel_properties"]["success_return_url"])
        self.assertEqual("http://shop.example/checkout/failed", payload["channel_properties"]["failure_return_url"])

    def test_checkout_live_environment_uses_live_sdk_and_fails_unknown_results_closed(self):
        self.app = self._make_app(ADYEN_ENVIRONMENT="live")
        self.client = self.app.test_client()

        response = self.client.get("/checkout")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("checkoutshopper-live.adyen.com/checkoutshopper/sdk/6.33.0/adyen.js", html)
        self.assertIn("Unknown terminal states should not be displayed as successful payments.", html)
        self.assertIn("window.location.href = failedUrl;", html)


if __name__ == "__main__":
    unittest.main()
