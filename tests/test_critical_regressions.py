import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app import create_app


class RawResponse:
    def __init__(self, payload):
        self.raw_response = json.dumps(payload)


class FakePaymentsApi:
    def __init__(self):
        self.last_payload = None

    def payments(self, payload):
        self.last_payload = payload
        return RawResponse({"resultCode": "Authorised"})

    def payment_methods(self, payload):
        self.last_payload = payload
        return RawResponse({"paymentMethods": []})


class FakeAdyenClient:
    def __init__(self):
        self.checkout = Mock()
        self.checkout.payments_api = FakePaymentsApi()


class FakeXenditResponse:
    ok = True
    text = "{}"
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def make_app(extra_config=None):
    config = {
        "TESTING": True,
        "ADYEN_API_KEY": "adyen-api-key",
        "ADYEN_CLIENT_KEY": "adyen-client-key",
        "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
        "ADYEN_ENVIRONMENT": "test",
        "XENDIT_SECRET_KEY": "xendit-secret",
    }
    if extra_config:
        config.update(extra_config)
    return create_app(config)


class CriticalRegressionTests(unittest.TestCase):
    def test_adyen_management_writes_require_configured_token(self):
        app = make_app({"ADYEN_MANAGEMENT_WRITE_TOKEN": ""})
        with app.test_client() as client, patch("app.routes.api.requests.patch") as patch_request:
            resp = client.patch("/api/adyen/stores/store-123", json={"splitConfiguration": {"splitConfigurationId": "sc"}})

        self.assertEqual(resp.status_code, 403)
        patch_request.assert_not_called()

    def test_adyen_management_writes_accept_valid_token_only(self):
        app = make_app({"ADYEN_MANAGEMENT_WRITE_TOKEN": "write-token"})
        mock_response = Mock(ok=True, text="{}", status_code=200)
        mock_response.json.return_value = {"id": "store-123"}
        with app.test_client() as client, patch("app.routes.api.requests.patch", return_value=mock_response) as patch_request:
            forbidden = client.patch("/api/adyen/stores/store-123", json={"description": "changed"})
            allowed = client.patch(
                "/api/adyen/stores/store-123",
                headers={"Authorization": "Bearer write-token"},
                json={"description": "changed"},
            )

        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
        patch_request.assert_called_once()

    def test_adyen_payments_overwrites_client_controlled_money_and_redirect_fields(self):
        app = make_app()
        fake_adyen = FakeAdyenClient()
        with app.test_client() as client, patch("app.routes.api.get_adyen_client", return_value=fake_adyen):
            resp = client.post(
                "/api/adyen/payments",
                json={
                    "amount": {"value": 1, "currency": "USD"},
                    "merchantAccount": "attacker-merchant",
                    "reference": "attacker-ref",
                    "returnUrl": "https://evil.example/complete",
                    "channel": "iOS",
                    "paymentMethod": {"type": "scheme"},
                },
            )

        self.assertEqual(resp.status_code, 200)
        payload = fake_adyen.checkout.payments_api.last_payload
        self.assertEqual(payload["amount"], {"value": 9498, "currency": "EUR"})
        self.assertEqual(payload["merchantAccount"], "merchant-account")
        self.assertEqual(payload["returnUrl"], "http://localhost/checkout/return")
        self.assertEqual(payload["channel"], "Web")
        self.assertTrue(payload["reference"].startswith("ref-"))
        self.assertNotEqual(payload["reference"], "attacker-ref")

    def test_adyen_alipay_discount_is_computed_server_side(self):
        app = make_app()
        fake_adyen = FakeAdyenClient()
        with app.test_client() as client, patch("app.routes.api.get_adyen_client", return_value=fake_adyen):
            resp = client.post(
                "/api/adyen/payments",
                json={
                    "amount": {"value": 1, "currency": "EUR"},
                    "paymentMethod": {"type": "alipay"},
                },
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(fake_adyen.checkout.payments_api.last_payload["amount"], {"value": 6649, "currency": "EUR"})

    def test_image_host_destructive_delete_requires_token(self):
        app = make_app({"IMAGE_HOST_DELETE_TOKEN": ""})
        with tempfile.TemporaryDirectory() as tmpdir:
            app.static_folder = tmpdir
            upload_dir = Path(tmpdir) / "uploads_tmp"
            upload_dir.mkdir()
            existing = upload_dir / "existing.png"
            existing.write_bytes(b"existing-image")

            with app.test_client() as client:
                resp = client.post("/api/image-host/delete-all")

            self.assertEqual(resp.status_code, 403)
            self.assertTrue(existing.exists())

    def test_overquota_upload_deletes_only_new_file(self):
        app = make_app()
        with tempfile.TemporaryDirectory() as tmpdir:
            app.static_folder = tmpdir
            upload_dir = Path(tmpdir) / "uploads_tmp"
            upload_dir.mkdir()
            existing = upload_dir / "existing.png"
            existing.write_bytes(b"existing-image")

            with patch("app.routes.api.IMAGE_HOST_MAX_BYTES", 16):
                with app.test_client() as client:
                    resp = client.post(
                        "/api/image-host/upload",
                        data={"image": (io.BytesIO(b"new-image-content"), "new.png")},
                        content_type="multipart/form-data",
                    )

            self.assertEqual(resp.status_code, 507)
            self.assertTrue(existing.exists())
            self.assertEqual([path.name for path in upload_dir.iterdir()], ["existing.png"])

    def test_xendit_payment_request_ignores_client_amount_and_return_urls(self):
        captured = {}

        def fake_post(url, json=None, **kwargs):
            captured["payload"] = json
            return FakeXenditResponse({
                "id": "payment-request-id",
                "actions": [{"type": "REDIRECT_CUSTOMER", "value": "https://xendit.example/pay"}],
            })

        app = make_app()
        with app.test_client() as client, patch("app.routes.api.requests.post", side_effect=fake_post):
            resp = client.post(
                "/api/xendit/payment-request",
                json={
                    "channel_code": "GRABPAY",
                    "amount": 1,
                    "success_return_url": "https://evil.example/success",
                    "failure_return_url": "https://evil.example/failure",
                },
            )

        self.assertEqual(resp.status_code, 200)
        payload = captured["payload"]
        self.assertEqual(payload["request_amount"], 50)
        self.assertEqual(payload["channel_properties"]["success_return_url"], "http://localhost/checkout/success")
        self.assertEqual(payload["channel_properties"]["failure_return_url"], "http://localhost/checkout/failed")

    def test_xendit_session_ignores_client_amount_currency_and_origin(self):
        captured = {}

        def fake_post(url, json=None, **kwargs):
            captured["payload"] = json
            return FakeXenditResponse({"components_sdk_key": "sdk-key"})

        app = make_app()
        with app.test_client() as client, patch("app.routes.api.requests.post", side_effect=fake_post):
            resp = client.post(
                "/api/xendit/sessions",
                json={
                    "amount": 1,
                    "currency": "USD",
                    "country": "US",
                    "origin": "https://evil.example",
                },
            )

        self.assertEqual(resp.status_code, 200)
        payload = captured["payload"]
        self.assertEqual(payload["amount"], 50000)
        self.assertEqual(payload["currency"], "IDR")
        self.assertEqual(payload["country"], "ID")
        self.assertNotIn("https://evil.example", payload["components_configuration"]["origins"])


if __name__ == "__main__":
    unittest.main()
