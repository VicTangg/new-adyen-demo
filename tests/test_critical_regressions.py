import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.routes.pages import get_checkout_total_cents


class FakeResponse:
    def __init__(self, payload, ok=True, status_code=200):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code
        self.text = "{}"

    def json(self):
        return self._payload


class CriticalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "IMAGE_HOST_MAX_BYTES": 1024,
            "IMAGE_HOST_DELETE_TOKEN": "delete-token",
            "XENDIT_SECRET_KEY": "xendit-secret",
            "XENDIT_ALLOWED_ORIGINS": "",
        })
        self.app.static_folder = self.tmpdir.name
        self.client = self.app.test_client()
        self.upload_dir = Path(self.tmpdir.name) / "uploads_tmp"
        self.upload_dir.mkdir()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_image_host_delete_all_requires_token(self):
        existing = self.upload_dir / "existing.png"
        existing.write_bytes(b"existing image")

        denied = self.client.post("/api/image-host/delete-all")
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(existing.exists())

        allowed = self.client.post(
            "/api/image-host/delete-all",
            headers={"X-Image-Host-Delete-Token": "delete-token"},
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertFalse(existing.exists())

    def test_over_quota_image_upload_preserves_existing_files(self):
        existing = self.upload_dir / "existing.png"
        existing.write_bytes(b"x" * 900)

        response = self.client.post(
            "/api/image-host/upload",
            data={"image": (io.BytesIO(b"y" * 200), "new.png")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 507)
        self.assertTrue(existing.exists())
        self.assertEqual([path.name for path in self.upload_dir.iterdir()], ["existing.png"])

    def test_xendit_session_uses_server_amount_and_origins(self):
        with patch("app.routes.api.requests.post") as post:
            post.return_value = FakeResponse({"components_sdk_key": "sdk-key", "id": "session-id"})

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
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["amount"], get_checkout_total_cents())
        self.assertEqual(payload["currency"], "IDR")
        self.assertEqual(payload["country"], "ID")
        self.assertNotIn("https://evil.example", payload["components_configuration"]["origins"])

    def test_xendit_payment_request_ignores_client_amount_and_return_urls(self):
        with patch("app.routes.api.requests.post") as post:
            post.return_value = FakeResponse({
                "id": "payment-id",
                "actions": [{"type": "REDIRECT_CUSTOMER", "value": "https://xendit.example/pay"}],
            })

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
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["request_amount"], 50)
        self.assertEqual(payload["channel_properties"]["success_return_url"], "http://localhost/checkout/success")
        self.assertEqual(payload["channel_properties"]["failure_return_url"], "http://localhost/checkout/failed")


if __name__ == "__main__":
    unittest.main()
