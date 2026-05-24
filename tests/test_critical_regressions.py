import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app


class FakeResponse:
    def __init__(self, payload, ok=True, status_code=200):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class CriticalRegressionTests(unittest.TestCase):
    def create_client(self, **config):
        app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant",
            "ADYEN_ENVIRONMENT": "test",
            "XENDIT_SECRET_KEY": "xendit-key",
            **config,
        })
        return app, app.test_client()

    def test_management_write_requires_configured_token(self):
        _app, client = self.create_client(ADYEN_MANAGEMENT_WRITE_TOKEN="secret")

        with patch("app.routes.api.requests.patch") as request_patch:
            response = client.patch(
                "/api/adyen/stores/store-1",
                json={"splitConfiguration": {"balanceAccountId": "BA1"}},
            )

        self.assertEqual(response.status_code, 403)
        request_patch.assert_not_called()

    def test_management_write_allows_matching_bearer_token(self):
        _app, client = self.create_client(ADYEN_MANAGEMENT_WRITE_TOKEN="secret")

        with patch("app.routes.api.requests.patch", return_value=FakeResponse({"id": "store-1"})) as request_patch:
            response = client.patch(
                "/api/adyen/stores/store-1",
                headers={"Authorization": "Bearer secret"},
                json={"splitConfiguration": {"balanceAccountId": "BA1"}},
            )

        self.assertEqual(response.status_code, 200)
        request_patch.assert_called_once()

    def test_adyen_payment_amount_is_server_authoritative(self):
        captured = {}

        class FakePaymentsApi:
            def payments(self, payload):
                captured.update(payload)

                class Result:
                    raw_response = json.dumps({"resultCode": "Authorised"})

                return Result()

        class FakeAdyen:
            class Checkout:
                payments_api = FakePaymentsApi()

            checkout = Checkout()

        _app, client = self.create_client()

        with patch("app.routes.api.get_adyen_client", return_value=FakeAdyen()):
            response = client.post(
                "/api/adyen/payments",
                json={
                    "amount": {"value": 1, "currency": "EUR"},
                    "paymentMethod": {"type": "scheme"},
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["amount"], {"value": 9498, "currency": "EUR"})

    def test_xendit_session_ignores_client_amount_and_origin(self):
        _app, client = self.create_client()

        with patch("app.routes.api.requests.post", return_value=FakeResponse({"components_sdk_key": "sdk"})) as post:
            response = client.post(
                "/api/xendit/sessions",
                json={
                    "amount": 1,
                    "currency": "PHP",
                    "country": "PH",
                    "origin": "https://attacker.example",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["amount"], 50000)
        self.assertEqual(payload["currency"], "IDR")
        self.assertEqual(payload["country"], "ID")
        self.assertNotIn("https://attacker.example", payload["components_configuration"]["origins"])

    def test_xendit_payment_request_ignores_client_amount_and_return_urls(self):
        _app, client = self.create_client()

        with patch("app.routes.api.requests.post", return_value=FakeResponse({
            "id": "pr-1",
            "actions": [{"type": "REDIRECT_CUSTOMER", "value": "https://xendit.example/pay"}],
        })) as post:
            response = client.post(
                "/api/xendit/payment-request",
                json={
                    "channel_code": "GRABPAY",
                    "amount": 1,
                    "success_return_url": "https://attacker.example/success",
                    "failure_return_url": "https://attacker.example/failure",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["request_amount"], 50)
        self.assertEqual(payload["channel_properties"]["success_return_url"], "http://localhost/checkout/success")
        self.assertEqual(payload["channel_properties"]["failure_return_url"], "http://localhost/checkout/failed")

    def test_image_host_delete_all_requires_token(self):
        app, client = self.create_client(IMAGE_HOST_DELETE_TOKEN="secret")

        with tempfile.TemporaryDirectory() as tmp:
            app.static_folder = tmp
            uploads = Path(tmp) / "uploads_tmp"
            uploads.mkdir()
            existing = uploads / "existing.png"
            existing.write_bytes(b"old")

            response = client.post("/api/image-host/delete-all")

            self.assertEqual(response.status_code, 403)
            self.assertTrue(existing.exists())

    def test_over_quota_upload_deletes_only_new_file(self):
        app, client = self.create_client()

        with tempfile.TemporaryDirectory() as tmp:
            app.static_folder = tmp
            uploads = Path(tmp) / "uploads_tmp"
            uploads.mkdir()
            existing = uploads / "existing.png"
            existing.write_bytes(b"old-data")

            with patch("app.routes.api.IMAGE_HOST_MAX_BYTES", 10):
                response = client.post(
                    "/api/image-host/upload",
                    data={"image": (io.BytesIO(b"new-data"), "new.png", "image/png")},
                    content_type="multipart/form-data",
                )

            self.assertEqual(response.status_code, 507)
            self.assertEqual([path.name for path in uploads.iterdir()], ["existing.png"])


if __name__ == "__main__":
    unittest.main()
