import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from app.routes import api as api_module


class CriticalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        static_dir = Path(self.tmp.name) / "static"
        static_dir.mkdir()
        self.app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_CLIENT_KEY": "adyen-client-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "XENDIT_SECRET_KEY": "xendit-secret-key",
            "IMAGE_HOST_DELETE_TOKEN": "delete-secret",
        })
        self.app.static_folder = str(static_dir)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def _image_dir(self):
        image_dir = Path(self.app.static_folder) / api_module.IMAGE_HOST_DIR_NAME
        image_dir.mkdir(parents=True, exist_ok=True)
        return image_dir

    def test_image_host_list_and_over_quota_upload_do_not_delete_existing_images(self):
        image_dir = self._image_dir()
        existing = image_dir / "existing.png"
        existing.write_bytes(b"123456789")

        with patch.object(api_module, "IMAGE_HOST_MAX_BYTES", 10):
            list_resp = self.client.get("/api/image-host/list")
            self.assertEqual(list_resp.status_code, 200)
            self.assertTrue(existing.exists())

            upload_resp = self.client.post(
                "/api/image-host/upload",
                data={"image": (io.BytesIO(b"abcde"), "new.png", "image/png")},
                content_type="multipart/form-data",
            )

        self.assertEqual(upload_resp.status_code, 507)
        self.assertTrue(existing.exists())
        self.assertEqual([path.name for path in image_dir.iterdir()], ["existing.png"])

    def test_image_host_delete_all_requires_configured_token(self):
        image_dir = self._image_dir()
        existing = image_dir / "existing.png"
        existing.write_bytes(b"image")

        denied = self.client.post("/api/image-host/delete-all")
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(existing.exists())

        allowed = self.client.post(
            "/api/image-host/delete-all",
            headers={"X-Image-Host-Delete-Token": "delete-secret"},
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertFalse(existing.exists())

    def test_adyen_management_writes_require_token_before_patch(self):
        with patch("app.routes.api.requests.patch") as mock_patch:
            denied = self.client.patch(
                "/api/adyen/stores/store-123",
                json={"splitConfiguration": {"splitConfigurationId": "attacker"}},
            )
        self.assertEqual(denied.status_code, 403)
        mock_patch.assert_not_called()

        self.app.config["ADYEN_MANAGEMENT_WRITE_TOKEN"] = "management-secret"
        with patch("app.routes.api.requests.patch") as mock_patch:
            mock_patch.return_value.ok = True
            mock_patch.return_value.text = "{}"
            mock_patch.return_value.json.return_value = {"id": "store-123"}
            allowed = self.client.patch(
                "/api/adyen/stores/store-123",
                json={"splitConfiguration": {"splitConfigurationId": "safe"}},
                headers={"Authorization": "Bearer management-secret"},
            )

        self.assertEqual(allowed.status_code, 200)
        mock_patch.assert_called_once()

    def test_adyen_payments_overwrites_client_controlled_money_and_routing_fields(self):
        captured = {}

        class FakePaymentsApi:
            def payments(self, payload):
                captured["payload"] = json.loads(json.dumps(payload))
                return SimpleNamespace(raw_response=json.dumps({"resultCode": "Authorised"}))

        fake_adyen = SimpleNamespace(checkout=SimpleNamespace(payments_api=FakePaymentsApi()))

        with patch("app.routes.api.get_adyen_client", return_value=fake_adyen):
            resp = self.client.post(
                "/api/adyen/payments",
                json={
                    "amount": {"value": 1, "currency": "USD"},
                    "merchantAccount": "attacker-merchant",
                    "reference": "attacker-reference",
                    "returnUrl": "https://evil.example/return",
                    "channel": "iOS",
                    "origin": "https://evil.example",
                    "paymentMethod": {"type": "scheme"},
                },
            )

        self.assertEqual(resp.status_code, 200)
        payload = captured["payload"]
        self.assertEqual(payload["amount"], {"value": 9498, "currency": "EUR"})
        self.assertEqual(payload["merchantAccount"], "merchant-account")
        self.assertNotEqual(payload["reference"], "attacker-reference")
        self.assertEqual(payload["returnUrl"], "http://localhost/checkout/return")
        self.assertEqual(payload["channel"], "Web")
        self.assertEqual(payload["origin"], "https://localhost")

    def test_adyen_payments_applies_alipay_discount_server_side_only(self):
        captured = {}

        class FakePaymentsApi:
            def payments(self, payload):
                captured["payload"] = json.loads(json.dumps(payload))
                return SimpleNamespace(raw_response=json.dumps({"resultCode": "Authorised"}))

        fake_adyen = SimpleNamespace(checkout=SimpleNamespace(payments_api=FakePaymentsApi()))

        with patch("app.routes.api.get_adyen_client", return_value=fake_adyen):
            resp = self.client.post(
                "/api/adyen/payments",
                json={"amount": {"value": 1, "currency": "USD"}, "paymentMethod": {"type": "alipay"}},
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(captured["payload"]["amount"], {"value": 6649, "currency": "EUR"})

    def test_xendit_session_uses_server_amount_currency_country_and_allowed_origins(self):
        with patch("app.routes.api.requests.post") as mock_post:
            mock_post.return_value.ok = True
            mock_post.return_value.text = "{}"
            mock_post.return_value.json.return_value = {"id": "session-id", "components_sdk_key": "sdk-key"}
            resp = self.client.post(
                "/api/xendit/sessions",
                json={
                    "amount": 1,
                    "currency": "USD",
                    "country": "US",
                    "origin": "https://evil.example",
                },
            )

        self.assertEqual(resp.status_code, 200)
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["amount"], 9498)
        self.assertEqual(payload["currency"], "IDR")
        self.assertEqual(payload["country"], "ID")
        origins = payload["components_configuration"]["origins"]
        self.assertIn("https://localhost", origins)
        self.assertNotIn("https://evil.example", origins)

    def test_xendit_payment_request_uses_server_amount_and_return_urls(self):
        with patch("app.routes.api.requests.post") as mock_post:
            mock_post.return_value.ok = True
            mock_post.return_value.text = "{}"
            mock_post.return_value.json.return_value = {
                "id": "payment-request-id",
                "actions": [{"type": "REDIRECT_CUSTOMER", "value": "https://pay.example/redirect"}],
            }
            resp = self.client.post(
                "/api/xendit/payment-request",
                json={
                    "channel_code": "GRABPAY",
                    "amount": 1,
                    "success_return_url": "https://evil.example/success",
                    "failure_return_url": "https://evil.example/failure",
                },
            )

        self.assertEqual(resp.status_code, 200)
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["request_amount"], 50)
        self.assertEqual(payload["channel_properties"]["success_return_url"], "http://localhost/checkout/success")
        self.assertEqual(payload["channel_properties"]["failure_return_url"], "http://localhost/checkout/failed")

    def test_checkout_template_uses_live_cdn_and_fails_closed_for_unknown_result_codes(self):
        self.app.config["ADYEN_ENVIRONMENT"] = "live"

        resp = self.client.get("/checkout")
        body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/6.33.0/adyen.js", body)
        self.assertNotIn("https://checkoutshopper-test.adyen.com/checkoutshopper/sdk/6.33.0/adyen.js", body)
        self.assertIn("Unknown result codes must not be treated as paid.", body)
        self.assertNotIn("redirect to success to be safe", body)


if __name__ == "__main__":
    unittest.main()
