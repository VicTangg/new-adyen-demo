import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from app.routes.pages import CHECKOUT_CURRENCY, get_checkout_total_cents


class FakeAdyenResult:
    def __init__(self, payload):
        self.raw_response = json.dumps(payload)


class CapturingAdyenPaymentsApi:
    def __init__(self):
        self.payment_methods_payload = None
        self.payments_payload = None

    def payment_methods(self, payload):
        self.payment_methods_payload = copy.deepcopy(payload)
        return FakeAdyenResult({"paymentMethods": []})

    def payments(self, payload):
        self.payments_payload = copy.deepcopy(payload)
        return FakeAdyenResult({"resultCode": "Authorised"})


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.text = json.dumps(payload)

    def json(self):
        return copy.deepcopy(self._payload)


class CriticalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_CLIENT_KEY": "adyen-client-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "management-token",
            "IMAGE_HOST_DELETE_TOKEN": "delete-token",
            "XENDIT_SECRET_KEY": "xendit-secret-key",
        })
        self.client = self.app.test_client()

    def _adyen_client(self, payments_api):
        return SimpleNamespace(checkout=SimpleNamespace(payments_api=payments_api))

    def test_adyen_payment_methods_uses_server_checkout_amount(self):
        payments_api = CapturingAdyenPaymentsApi()

        with patch("app.routes.api.get_adyen_client", return_value=self._adyen_client(payments_api)):
            response = self.client.post("/api/adyen/paymentMethods", json={
                "amount": {"value": 1, "currency": "USD"},
                "countryCode": "NL",
                "channel": "Web",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            payments_api.payment_methods_payload["amount"],
            {"value": get_checkout_total_cents(), "currency": CHECKOUT_CURRENCY},
        )

    def test_adyen_payments_overrides_client_amount_and_redirect_fields(self):
        payments_api = CapturingAdyenPaymentsApi()

        with patch("app.routes.api.get_adyen_client", return_value=self._adyen_client(payments_api)):
            response = self.client.post("/api/adyen/payments", json={
                "amount": {"value": 1, "currency": "USD"},
                "reference": "attacker-reference",
                "returnUrl": "https://evil.example/return",
                "merchantAccount": "attacker-merchant",
                "channel": "iOS",
                "paymentMethod": {"type": "scheme"},
            })

        self.assertEqual(response.status_code, 200)
        payload = payments_api.payments_payload
        self.assertEqual(payload["amount"], {"value": get_checkout_total_cents(), "currency": CHECKOUT_CURRENCY})
        self.assertEqual(payload["returnUrl"], "http://localhost/checkout/return")
        self.assertEqual(payload["merchantAccount"], "merchant-account")
        self.assertEqual(payload["channel"], "Web")
        self.assertNotEqual(payload["reference"], "attacker-reference")
        self.assertTrue(payload["reference"].startswith("ref-"))

    def test_adyen_payments_applies_server_side_alipay_discount_only(self):
        payments_api = CapturingAdyenPaymentsApi()

        with patch("app.routes.api.get_adyen_client", return_value=self._adyen_client(payments_api)):
            response = self.client.post("/api/adyen/payments", json={
                "amount": {"value": 1, "currency": "USD"},
                "paymentMethod": {"type": "alipay"},
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            payments_api.payments_payload["amount"],
            {"value": round(get_checkout_total_cents() * 0.7), "currency": CHECKOUT_CURRENCY},
        )

    def test_management_write_requires_configured_token(self):
        with patch("app.routes.api.requests.patch") as mock_patch:
            response = self.client.patch("/api/adyen/stores/store-1", json={"splitConfiguration": {}})

        self.assertEqual(response.status_code, 401)
        mock_patch.assert_not_called()

    def test_management_write_accepts_bearer_token(self):
        captured = {}

        def fake_patch(url, headers, json, timeout):
            captured["url"] = url
            captured["json"] = copy.deepcopy(json)
            return FakeResponse({"id": "store-1"})

        with patch("app.routes.api.requests.patch", side_effect=fake_patch):
            response = self.client.patch(
                "/api/adyen/stores/store-1",
                json={"splitConfiguration": {"splitConfigurationId": "split-1"}},
                headers={"Authorization": "Bearer management-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("/stores/store-1", captured["url"])
        self.assertEqual(captured["json"]["splitConfiguration"]["splitConfigurationId"], "split-1")

    def test_image_delete_all_requires_token_and_preserves_files_without_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.app.static_folder = tmp
            upload_dir = Path(tmp) / "uploads_tmp"
            upload_dir.mkdir()
            old_file = upload_dir / "old.png"
            old_file.write_bytes(b"existing")

            response = self.client.post("/api/image-host/delete-all")
            self.assertEqual(response.status_code, 401)
            self.assertTrue(old_file.exists())

            response = self.client.post(
                "/api/image-host/delete-all",
                headers={"X-Image-Host-Delete-Token": "delete-token"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertFalse(old_file.exists())

    def test_over_quota_upload_deletes_only_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.app.static_folder = tmp
            upload_dir = Path(tmp) / "uploads_tmp"
            upload_dir.mkdir()
            old_file = upload_dir / "old.png"
            old_file.write_bytes(b"existing")

            with patch("app.routes.api.IMAGE_HOST_MAX_BYTES", len(b"existing") + 1):
                response = self.client.post(
                    "/api/image-host/upload",
                    data={"image": (io.BytesIO(b"new"), "new.png")},
                    content_type="multipart/form-data",
                )

            self.assertEqual(response.status_code, 507)
            self.assertTrue(old_file.exists())
            self.assertEqual([path.name for path in upload_dir.iterdir()], ["old.png"])

    def test_image_list_does_not_purge_existing_over_quota_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.app.static_folder = tmp
            upload_dir = Path(tmp) / "uploads_tmp"
            upload_dir.mkdir()
            old_file = upload_dir / "old.png"
            old_file.write_bytes(b"existing")

            with patch("app.routes.api.IMAGE_HOST_MAX_BYTES", 1):
                response = self.client.get("/api/image-host/list")

            self.assertEqual(response.status_code, 200)
            self.assertTrue(old_file.exists())

    def test_xendit_session_uses_server_amount_and_origins(self):
        captured = {}

        def fake_post(url, json, auth, headers, timeout):
            captured["json"] = copy.deepcopy(json)
            return FakeResponse({"components_sdk_key": "sdk-key"})

        with patch("app.routes.api.requests.post", side_effect=fake_post):
            response = self.client.post("/api/xendit/sessions", json={
                "amount": 1,
                "currency": "USD",
                "country": "US",
                "origin": "https://evil.example",
            })

        self.assertEqual(response.status_code, 200)
        payload = captured["json"]
        self.assertEqual(payload["amount"], get_checkout_total_cents())
        self.assertEqual(payload["currency"], "IDR")
        self.assertEqual(payload["country"], "ID")
        self.assertNotIn("https://evil.example", payload["components_configuration"]["origins"])

    def test_xendit_payment_request_uses_server_amount_and_return_urls(self):
        captured = {}

        def fake_post(url, json, auth, headers, timeout):
            captured["json"] = copy.deepcopy(json)
            return FakeResponse({
                "id": "payment-request-id",
                "actions": [{"type": "REDIRECT_CUSTOMER", "value": "https://pay.example/redirect"}],
            })

        with patch("app.routes.api.requests.post", side_effect=fake_post):
            response = self.client.post("/api/xendit/payment-request", json={
                "channel_code": "GRABPAY",
                "amount": 1,
                "success_return_url": "https://evil.example/success",
                "failure_return_url": "https://evil.example/failure",
            })

        self.assertEqual(response.status_code, 200)
        payload = captured["json"]
        self.assertEqual(payload["request_amount"], 50)
        self.assertEqual(payload["channel_properties"]["success_return_url"], "http://localhost/checkout/success")
        self.assertEqual(payload["channel_properties"]["failure_return_url"], "http://localhost/checkout/failed")

    def test_checkout_live_environment_uses_live_adyen_cdn_and_fails_closed(self):
        app = create_app({
            "TESTING": True,
            "ADYEN_CLIENT_KEY": "adyen-client-key",
            "ADYEN_ENVIRONMENT": "live",
        })
        response = app.test_client().get("/checkout")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("checkoutshopper-live.adyen.com", body)
        self.assertNotIn("checkoutshopper-test.adyen.com/checkoutshopper/sdk/6.33.0", body)
        self.assertIn("Unknown terminal states must not show a successful payment.", body)
        self.assertIn("window.location.href = failedUrl;", body)


if __name__ == "__main__":
    unittest.main()
