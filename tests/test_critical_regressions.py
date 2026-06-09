import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app import create_app


class _RawResponse:
    def __init__(self, payload):
        self.raw_response = json.dumps(payload)


class CriticalRegressionTests(unittest.TestCase):
    def create_client(self, **config):
        base_config = {
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-key",
            "ADYEN_CLIENT_KEY": "adyen-client-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "XENDIT_SECRET_KEY": "xendit-key",
        }
        base_config.update(config)
        app = create_app(base_config)
        return app, app.test_client()

    def test_adyen_payment_uses_server_amount_and_return_url(self):
        _, client = self.create_client()
        captured = {}

        class FakePaymentsApi:
            def payments(self, payload):
                captured.update(payload)
                return _RawResponse({"resultCode": "Authorised"})

        fake_adyen = SimpleNamespace(
            checkout=SimpleNamespace(payments_api=FakePaymentsApi())
        )

        with patch("app.routes.api.get_adyen_client", return_value=fake_adyen):
            response = client.post("/api/adyen/payments", json={
                "amount": {"value": 1, "currency": "USD"},
                "merchantAccount": "attacker-merchant",
                "reference": "attacker-reference",
                "returnUrl": "https://attacker.example/complete",
                "channel": "iOS",
                "paymentMethod": {"type": "scheme"},
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["amount"], {"value": 9498, "currency": "EUR"})
        self.assertEqual(captured["merchantAccount"], "merchant-account")
        self.assertEqual(captured["returnUrl"], "http://localhost/checkout/return")
        self.assertEqual(captured["channel"], "Web")
        self.assertNotEqual(captured["reference"], "attacker-reference")

    def test_adyen_payment_methods_uses_server_amount(self):
        _, client = self.create_client()
        captured = {}

        class FakePaymentsApi:
            def payment_methods(self, payload):
                captured.update(payload)
                return _RawResponse({"paymentMethods": []})

        fake_adyen = SimpleNamespace(
            checkout=SimpleNamespace(payments_api=FakePaymentsApi())
        )

        with patch("app.routes.api.get_adyen_client", return_value=fake_adyen):
            response = client.post("/api/adyen/paymentMethods", json={
                "amount": {"value": 1, "currency": "USD"},
                "channel": "iOS",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["amount"], {"value": 9498, "currency": "EUR"})
        self.assertEqual(captured["channel"], "Web")
        self.assertEqual(captured["merchantAccount"], "merchant-account")

    def test_adyen_management_writes_require_token(self):
        _, client = self.create_client(ADYEN_MANAGEMENT_WRITE_TOKEN="secret-token")

        with patch("app.routes.api.requests.patch") as patch_request:
            response = client.patch("/api/adyen/stores/store-id", json={
                "splitConfiguration": {"balanceAccountId": "BA0001"}
            })

        self.assertEqual(response.status_code, 403)
        patch_request.assert_not_called()

    def test_adyen_management_writes_allow_valid_bearer_token(self):
        _, client = self.create_client(ADYEN_MANAGEMENT_WRITE_TOKEN="secret-token")
        response_payload = {"id": "store-id"}
        patch_response = Mock(ok=True, status_code=200, text=json.dumps(response_payload))
        patch_response.json.return_value = response_payload

        with patch("app.routes.api.requests.patch", return_value=patch_response) as patch_request:
            response = client.patch(
                "/api/adyen/stores/store-id",
                json={"splitConfiguration": {"balanceAccountId": "BA0001"}},
                headers={"Authorization": "Bearer secret-token"},
            )

        self.assertEqual(response.status_code, 200)
        patch_request.assert_called_once()

    def test_xendit_session_ignores_client_amount_currency_country_and_origin(self):
        _, client = self.create_client()
        captured = {}
        post_response = Mock(ok=True, status_code=200, text='{"components_sdk_key":"key"}')
        post_response.json.return_value = {"components_sdk_key": "key"}

        def fake_post(url, json=None, **kwargs):
            captured.update(json)
            return post_response

        with patch("app.routes.api.requests.post", side_effect=fake_post):
            response = client.post("/api/xendit/sessions", json={
                "amount": 1,
                "currency": "USD",
                "country": "US",
                "origin": "https://attacker.example",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["amount"], 9498)
        self.assertEqual(captured["currency"], "IDR")
        self.assertEqual(captured["country"], "ID")
        self.assertNotIn(
            "https://attacker.example",
            captured["components_configuration"]["origins"],
        )

    def test_xendit_payment_request_ignores_client_amount_and_return_urls(self):
        _, client = self.create_client()
        captured = {}
        post_response = Mock(ok=True, status_code=200, text='{"actions":[]}')
        post_response.json.return_value = {
            "id": "payment-request-id",
            "actions": [{"type": "REDIRECT_CUSTOMER", "value": "https://pay.example"}],
        }

        def fake_post(url, json=None, **kwargs):
            captured.update(json)
            return post_response

        with patch("app.routes.api.requests.post", side_effect=fake_post):
            response = client.post("/api/xendit/payment-request", json={
                "channel_code": "GRABPAY",
                "amount": 0.01,
                "success_return_url": "https://attacker.example/success",
                "failure_return_url": "https://attacker.example/failure",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["request_amount"], 50)
        self.assertEqual(captured["channel_properties"]["success_return_url"], "http://localhost/checkout/success")
        self.assertEqual(captured["channel_properties"]["failure_return_url"], "http://localhost/checkout/failed")

    def test_image_host_over_quota_upload_preserves_existing_files(self):
        app, client = self.create_client()
        with tempfile.TemporaryDirectory() as static_dir:
            app.static_folder = static_dir
            upload_dir = Path(static_dir) / "uploads_tmp"
            upload_dir.mkdir()
            existing = upload_dir / "existing.png"
            existing.write_bytes(b"existing")

            with patch("app.routes.api.IMAGE_HOST_MAX_BYTES", 10):
                response = client.post(
                    "/api/image-host/upload",
                    data={"image": (io.BytesIO(b"new-file"), "new.png")},
                    content_type="multipart/form-data",
                )

            self.assertEqual(response.status_code, 507)
            self.assertTrue(existing.exists())
            self.assertEqual([path.name for path in upload_dir.iterdir()], ["existing.png"])

    def test_image_host_list_does_not_purge_over_quota_files(self):
        app, client = self.create_client()
        with tempfile.TemporaryDirectory() as static_dir:
            app.static_folder = static_dir
            upload_dir = Path(static_dir) / "uploads_tmp"
            upload_dir.mkdir()
            existing = upload_dir / "existing.png"
            existing.write_bytes(b"existing")

            with patch("app.routes.api.IMAGE_HOST_MAX_BYTES", 1):
                response = client.get("/api/image-host/list")

            self.assertEqual(response.status_code, 200)
            self.assertTrue(existing.exists())
            self.assertEqual(response.get_json()["images"][0]["filename"], "existing.png")

    def test_image_host_delete_all_requires_token(self):
        _, client = self.create_client(IMAGE_HOST_DELETE_TOKEN="delete-token")

        response = client.post("/api/image-host/delete-all")

        self.assertEqual(response.status_code, 403)

    def test_checkout_uses_live_adyen_cdn_in_live_environment(self):
        _, client = self.create_client(ADYEN_ENVIRONMENT="live")

        response = client.get("/checkout")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/6.33.0/adyen.js", html)
        self.assertIn("https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/6.33.0/adyen.css", html)
        self.assertNotIn("https://checkoutshopper-test.adyen.com/checkoutshopper/sdk/6.33.0/adyen.js", html)


if __name__ == "__main__":
    unittest.main()
