import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
import app.routes.api as api


class _FakeAdyenResult:
    def __init__(self, payload):
        self.raw_response = json.dumps(payload)


class _FakePaymentsApi:
    def __init__(self, captured):
        self._captured = captured

    def payment_methods(self, payload):
        self._captured["payment_methods"] = copy.deepcopy(payload)
        return _FakeAdyenResult({"paymentMethods": []})

    def payments(self, payload):
        self._captured["payments"] = copy.deepcopy(payload)
        return _FakeAdyenResult({"resultCode": "Authorised"})


class _FakeAdyenClient:
    def __init__(self, captured):
        self.checkout = SimpleNamespace(payments_api=_FakePaymentsApi(captured))


class CriticalRegressionTests(unittest.TestCase):
    def _app(self, **config):
        base_config = {
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-key",
            "ADYEN_CLIENT_KEY": "adyen-client",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "XENDIT_SECRET_KEY": "xendit-secret",
        }
        base_config.update(config)
        return create_app(base_config)

    def test_adyen_payments_overwrites_client_controlled_charge_fields(self):
        app = self._app()
        captured = {}

        with patch.object(api, "get_adyen_client", return_value=_FakeAdyenClient(captured)):
            response = app.test_client().post(
                "/api/adyen/payments",
                json={
                    "amount": {"value": 1, "currency": "USD"},
                    "merchantAccount": "attacker-merchant",
                    "reference": "attacker-reference",
                    "returnUrl": "https://attacker.example/return",
                    "origin": "https://attacker.example",
                    "paymentMethod": {"type": "scheme"},
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = captured["payments"]
        self.assertEqual(payload["amount"], {"value": 9498, "currency": "EUR"})
        self.assertEqual(payload["merchantAccount"], "merchant-account")
        self.assertEqual(payload["returnUrl"], "http://localhost/checkout/return")
        self.assertEqual(payload["origin"], "http://localhost")
        self.assertEqual(payload["channel"], "Web")
        self.assertNotEqual(payload["reference"], "attacker-reference")

    def test_adyen_payments_handles_null_amount_and_applies_alipay_discount_server_side(self):
        app = self._app()
        captured = {}

        with patch.object(api, "get_adyen_client", return_value=_FakeAdyenClient(captured)):
            response = app.test_client().post(
                "/api/adyen/payments",
                json={"amount": None, "paymentMethod": {"type": "alipay"}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["payments"]["amount"], {"value": 6649, "currency": "EUR"})

    def test_adyen_payment_methods_uses_server_cart_amount(self):
        app = self._app()
        captured = {}

        with patch.object(api, "get_adyen_client", return_value=_FakeAdyenClient(captured)):
            response = app.test_client().post(
                "/api/adyen/paymentMethods",
                json={"amount": {"value": 1, "currency": "USD"}, "countryCode": "US", "channel": "iOS"},
            )

        self.assertEqual(response.status_code, 200)
        payload = captured["payment_methods"]
        self.assertEqual(payload["amount"], {"value": 9498, "currency": "EUR"})
        self.assertEqual(payload["countryCode"], "NL")
        self.assertEqual(payload["channel"], "Web")

    def test_xendit_session_ignores_client_amount_currency_country_and_origin(self):
        app = self._app()
        captured = {}

        def fake_post(url, json=None, **kwargs):
            captured["url"] = url
            captured["payload"] = copy.deepcopy(json)
            return SimpleNamespace(ok=True, text="{}", json=lambda: {"components_sdk_key": "sdk-key"})

        with patch.object(api.requests, "post", side_effect=fake_post):
            response = app.test_client().post(
                "/api/xendit/sessions",
                json={
                    "amount": 1,
                    "currency": "USD",
                    "country": "US",
                    "origin": "https://attacker.example",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = captured["payload"]
        self.assertEqual(payload["amount"], 9498)
        self.assertEqual(payload["currency"], "IDR")
        self.assertEqual(payload["country"], "ID")
        self.assertNotIn("https://attacker.example", payload["components_configuration"]["origins"])

    def test_xendit_payment_request_ignores_client_amount_and_redirect_urls(self):
        app = self._app()
        captured = {}

        def fake_post(url, json=None, **kwargs):
            captured["payload"] = copy.deepcopy(json)
            return SimpleNamespace(
                ok=True,
                text="{}",
                json=lambda: {
                    "id": "payment-id",
                    "actions": [{"type": "REDIRECT_CUSTOMER", "value": "https://xendit.example/pay"}],
                },
            )

        with patch.object(api.requests, "post", side_effect=fake_post):
            response = app.test_client().post(
                "/api/xendit/payment-request",
                json={
                    "channel_code": "DANA",
                    "amount": 1,
                    "success_return_url": "https://attacker.example/success",
                    "failure_return_url": "https://attacker.example/failure",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = captured["payload"]
        self.assertEqual(payload["request_amount"], 50000)
        self.assertEqual(payload["channel_properties"]["success_return_url"], "http://localhost/checkout/success")
        self.assertEqual(payload["channel_properties"]["failure_return_url"], "http://localhost/checkout/failed")

    def test_management_patch_routes_require_write_token(self):
        app = self._app()
        client = app.test_client()

        with patch.object(api.requests, "patch") as patched:
            response = client.patch("/api/adyen/stores/store-1", json={"splitConfiguration": {}})
        self.assertEqual(response.status_code, 403)
        patched.assert_not_called()

        authed_app = self._app(ADYEN_MANAGEMENT_WRITE_TOKEN="secret-token")
        authed_client = authed_app.test_client()
        with patch.object(api.requests, "patch") as patched:
            patched.return_value = SimpleNamespace(ok=True, text="{}", json=lambda: {"ok": True})
            response = authed_client.patch(
                "/api/adyen/stores/store-1",
                json={"splitConfiguration": {"splitConfigurationId": "sc"}},
                headers={"X-Adyen-Management-Write-Token": "secret-token"},
            )

        self.assertEqual(response.status_code, 200)
        patched.assert_called_once()

    def test_image_host_list_does_not_delete_files_when_over_quota(self):
        app = self._app()
        with tempfile.TemporaryDirectory() as tmp:
            app.static_folder = tmp
            upload_dir = Path(tmp) / api.IMAGE_HOST_DIR_NAME
            upload_dir.mkdir()
            existing = upload_dir / "kept.png"
            existing.write_bytes(b"x" * 20)

            with patch.object(api, "IMAGE_HOST_MAX_BYTES", 10):
                response = app.test_client().get("/api/image-host/list")

            self.assertEqual(response.status_code, 200)
            self.assertTrue(existing.exists())

    def test_image_host_over_quota_upload_removes_only_new_file(self):
        app = self._app()
        with tempfile.TemporaryDirectory() as tmp:
            app.static_folder = tmp
            upload_dir = Path(tmp) / api.IMAGE_HOST_DIR_NAME
            upload_dir.mkdir()
            existing = upload_dir / "kept.png"
            existing.write_bytes(b"x" * 9990)

            with patch.object(api, "IMAGE_HOST_MAX_BYTES", 10000):
                response = app.test_client().post(
                    "/api/image-host/upload",
                    data={"image": (io.BytesIO(b"x" * 50), "new.png")},
                    content_type="multipart/form-data",
                )

            self.assertEqual(response.status_code, 507)
            self.assertTrue(existing.exists())
            self.assertEqual([p.name for p in upload_dir.iterdir()], ["kept.png"])

    def test_image_host_delete_all_requires_token(self):
        app = self._app()
        with tempfile.TemporaryDirectory() as tmp:
            app.static_folder = tmp
            upload_dir = Path(tmp) / api.IMAGE_HOST_DIR_NAME
            upload_dir.mkdir()
            existing = upload_dir / "kept.png"
            existing.write_bytes(b"x")

            response = app.test_client().post("/api/image-host/delete-all")
            self.assertEqual(response.status_code, 403)
            self.assertTrue(existing.exists())

        authed_app = self._app(IMAGE_HOST_DELETE_TOKEN="delete-token")
        with tempfile.TemporaryDirectory() as tmp:
            authed_app.static_folder = tmp
            upload_dir = Path(tmp) / api.IMAGE_HOST_DIR_NAME
            upload_dir.mkdir()
            existing = upload_dir / "kept.png"
            existing.write_bytes(b"x")

            response = authed_app.test_client().post(
                "/api/image-host/delete-all",
                headers={"Authorization": "Bearer delete-token"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertFalse(existing.exists())

    def test_checkout_template_fails_closed_and_uses_live_cdn_in_live_mode(self):
        app = self._app(ADYEN_ENVIRONMENT="live")
        response = app.test_client().get("/checkout")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("checkoutshopper-live.adyen.com", html)
        self.assertNotIn("Any other code: redirect to success", html)
        self.assertIn("window.location.href = failedUrl;", html)

    def test_env_example_uses_placeholders_not_credentials(self):
        env_example = Path(".env.example").read_text()

        self.assertIn("ADYEN_API_KEY=your_adyen_api_key", env_example)
        self.assertNotIn("AQEzhmfx", env_example)
        self.assertNotIn("VictorTangLimitedBP_HK_TEST", env_example)


if __name__ == "__main__":
    unittest.main()
