import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from app.routes import api
from app.routes.pages import CHECKOUT_CURRENCY, get_checkout_total_cents


class _FakeAdyenResult:
    raw_response = '{"resultCode": "Authorised"}'


class _FakeAdyenClient:
    def __init__(self):
        self.payments_payload = None
        self.payment_methods_payload = None
        payments_api = SimpleNamespace(
            payments=self._payments,
            payment_methods=self._payment_methods,
        )
        self.checkout = SimpleNamespace(payments_api=payments_api)

    def _payments(self, payload):
        self.payments_payload = payload
        return _FakeAdyenResult()

    def _payment_methods(self, payload):
        self.payment_methods_payload = payload
        return _FakeAdyenResult()


class _FakeResponse:
    def __init__(self, payload, ok=True, status_code=200):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code
        self.text = "body"

    def json(self):
        return self._payload


class CriticalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_CLIENT_KEY": "adyen-client-key",
            "ADYEN_MERCHANT_ACCOUNT": "MerchantAccount",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "management-token",
            "IMAGE_HOST_DELETE_TOKEN": "delete-token",
            "XENDIT_SECRET_KEY": "xendit-secret",
        })
        self.client = self.app.test_client()

    def test_adyen_payment_methods_uses_server_amount(self):
        fake_adyen = _FakeAdyenClient()
        with patch("app.routes.api.get_adyen_client", return_value=fake_adyen):
            resp = self.client.post("/api/adyen/paymentMethods", json={
                "amount": {"value": 1, "currency": "USD"},
                "countryCode": "US",
                "channel": "iOS",
            })

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            fake_adyen.payment_methods_payload["amount"],
            {"value": get_checkout_total_cents(), "currency": CHECKOUT_CURRENCY},
        )
        self.assertEqual(fake_adyen.payment_methods_payload["countryCode"], "NL")
        self.assertEqual(fake_adyen.payment_methods_payload["channel"], "Web")

    def test_adyen_payment_ignores_client_controlled_charge_fields(self):
        fake_adyen = _FakeAdyenClient()
        with patch("app.routes.api.get_adyen_client", return_value=fake_adyen):
            resp = self.client.post("/api/adyen/payments", json={
                "amount": {"value": 1, "currency": "USD"},
                "merchantAccount": "AttackerMerchant",
                "reference": "attacker-ref",
                "returnUrl": "https://evil.example/steal",
                "channel": "iOS",
                "paymentMethod": {"type": "scheme"},
            })

        self.assertEqual(resp.status_code, 200)
        payload = fake_adyen.payments_payload
        self.assertEqual(payload["amount"], {"value": get_checkout_total_cents(), "currency": CHECKOUT_CURRENCY})
        self.assertEqual(payload["merchantAccount"], "MerchantAccount")
        self.assertNotEqual(payload["reference"], "attacker-ref")
        self.assertEqual(payload["returnUrl"], "http://localhost/checkout/return")
        self.assertEqual(payload["channel"], "Web")

    def test_management_patch_requires_write_token(self):
        with patch("app.routes.api.requests.patch") as patch_request:
            resp = self.client.patch("/api/adyen/stores/store-1", json={"splitConfiguration": {}})

        self.assertEqual(resp.status_code, 403)
        patch_request.assert_not_called()

    def test_image_delete_all_requires_delete_token(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.app.static_folder = temp_dir
            image_dir = Path(temp_dir) / api.IMAGE_HOST_DIR_NAME
            image_dir.mkdir(parents=True, exist_ok=True)
            image_path = image_dir / "existing.jpg"
            image_path.write_bytes(b"existing")

            resp = self.client.post("/api/image-host/delete-all")

            self.assertEqual(resp.status_code, 403)
            self.assertTrue(image_path.exists())

    def test_over_quota_upload_removes_only_new_file(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(api, "IMAGE_HOST_MAX_BYTES", 10):
            self.app.static_folder = temp_dir
            image_dir = Path(temp_dir) / api.IMAGE_HOST_DIR_NAME
            image_dir.mkdir(parents=True, exist_ok=True)
            existing_path = image_dir / "existing.jpg"
            existing_path.write_bytes(b"existing")

            resp = self.client.post(
                "/api/image-host/upload",
                data={"image": (io.BytesIO(b"new-file"), "new.jpg")},
                content_type="multipart/form-data",
            )

            self.assertEqual(resp.status_code, 507)
            self.assertTrue(existing_path.exists())
            self.assertEqual([p.name for p in image_dir.iterdir()], ["existing.jpg"])

    def test_xendit_session_ignores_client_amount_currency_country_and_origin(self):
        captured = {}

        def fake_post(url, json, auth, headers, timeout):
            captured["payload"] = json
            return _FakeResponse({"components_sdk_key": "sdk-key"})

        with patch("app.routes.api.requests.post", side_effect=fake_post):
            resp = self.client.post("/api/xendit/sessions", json={
                "amount": 1,
                "currency": "USD",
                "country": "US",
                "origin": "https://evil.example",
            })

        self.assertEqual(resp.status_code, 200)
        payload = captured["payload"]
        self.assertEqual(payload["amount"], get_checkout_total_cents())
        self.assertEqual(payload["currency"], "IDR")
        self.assertEqual(payload["country"], "ID")
        self.assertNotIn("https://evil.example", payload["components_configuration"]["origins"])

    def test_xendit_payment_request_ignores_client_amount_and_return_urls(self):
        captured = {}

        def fake_post(url, json, auth, headers, timeout):
            captured["payload"] = json
            return _FakeResponse({
                "id": "payment-request-id",
                "actions": [{"type": "REDIRECT_CUSTOMER", "value": "https://checkout.example"}],
            })

        with patch("app.routes.api.requests.post", side_effect=fake_post):
            resp = self.client.post("/api/xendit/payment-request", json={
                "channel_code": "GRABPAY",
                "amount": 1,
                "success_return_url": "https://evil.example/success",
                "failure_return_url": "https://evil.example/failure",
            })

        self.assertEqual(resp.status_code, 200)
        payload = captured["payload"]
        self.assertEqual(payload["request_amount"], 50)
        self.assertEqual(payload["channel_properties"]["success_return_url"], "http://localhost/checkout/success")
        self.assertEqual(payload["channel_properties"]["failure_return_url"], "http://localhost/checkout/failed")

    def test_checkout_template_uses_live_sdk_host_and_fails_unknown_results_closed(self):
        response = self.client.get("/checkout", environ_overrides={"HTTP_HOST": "localhost"})
        self.assertIn(b"checkoutshopper-test.adyen.com", response.data)

        self.app.config["ADYEN_ENVIRONMENT"] = "live"
        response = self.client.get("/checkout", environ_overrides={"HTTP_HOST": "localhost"})
        self.assertIn(b"checkoutshopper-live.adyen.com", response.data)
        self.assertIn(b"window.location.href = failedUrl;", response.data)


if __name__ == "__main__":
    unittest.main()
