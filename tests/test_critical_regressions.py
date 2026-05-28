import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.routes import api
from app.routes.pages import get_checkout_total_cents


class MockResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = "{}"

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


class CriticalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "adyen-write-token",
            "IMAGE_HOST_DELETE_TOKEN": "image-delete-token",
            "XENDIT_SECRET_KEY": "xendit-secret",
            "PUBLIC_BASE_URL": "https://shop.example",
        })
        self.client = self.app.test_client()

        self.original_dir_name = api.IMAGE_HOST_DIR_NAME
        self.original_max_bytes = api.IMAGE_HOST_MAX_BYTES
        self.upload_dir_name = f"test_uploads_{next(tempfile._get_candidate_names())}"
        api.IMAGE_HOST_DIR_NAME = self.upload_dir_name
        api.IMAGE_HOST_MAX_BYTES = 16
        self.upload_dir = Path(self.app.static_folder) / self.upload_dir_name
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.upload_dir, ignore_errors=True)
        api.IMAGE_HOST_DIR_NAME = self.original_dir_name
        api.IMAGE_HOST_MAX_BYTES = self.original_max_bytes

    def test_image_delete_all_requires_token(self):
        existing = self.upload_dir / "keep.png"
        existing.write_bytes(b"data")

        response = self.client.post("/api/image-host/delete-all")

        self.assertEqual(response.status_code, 401)
        self.assertTrue(existing.exists())

    def test_image_delete_all_accepts_configured_token(self):
        existing = self.upload_dir / "delete.png"
        existing.write_bytes(b"data")

        response = self.client.post(
            "/api/image-host/delete-all",
            headers={"X-Image-Host-Delete-Token": "image-delete-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(existing.exists())

    def test_over_quota_upload_removes_only_new_file(self):
        existing = self.upload_dir / "existing.png"
        existing.write_bytes(b"safe")

        response = self.client.post(
            "/api/image-host/upload",
            data={"image": (io.BytesIO(b"x" * 20), "too-big.png")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 507)
        self.assertTrue(existing.exists())
        self.assertEqual([path.name for path in self.upload_dir.iterdir()], ["existing.png"])

    def test_adyen_management_patch_requires_write_token(self):
        with patch("app.routes.api.requests.patch") as mock_patch:
            response = self.client.patch(
                "/api/adyen/stores/store-id",
                json={"splitConfiguration": {"splitConfigurationId": "scid"}},
            )

        self.assertEqual(response.status_code, 401)
        mock_patch.assert_not_called()

    def test_adyen_management_patch_accepts_configured_write_token(self):
        with patch("app.routes.api.requests.patch", return_value=MockResponse(payload={"id": "store-id"})) as mock_patch:
            response = self.client.patch(
                "/api/adyen/stores/store-id",
                json={"splitConfiguration": {"splitConfigurationId": "scid"}},
                headers={"Authorization": "Bearer adyen-write-token"},
            )

        self.assertEqual(response.status_code, 200)
        mock_patch.assert_called_once()

    def test_xendit_session_ignores_client_payment_controls(self):
        captured = {}

        def fake_post(url, json=None, **kwargs):
            captured["payload"] = json
            return MockResponse(payload={"components_sdk_key": "sdk-key"})

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
        payload = captured["payload"]
        self.assertEqual(payload["amount"], get_checkout_total_cents())
        self.assertEqual(payload["currency"], "IDR")
        self.assertEqual(payload["country"], "ID")
        self.assertNotIn("https://evil.example", payload["components_configuration"]["origins"])

    def test_xendit_payment_request_ignores_client_amount_and_return_urls(self):
        captured = {}

        def fake_post(url, json=None, **kwargs):
            captured["payload"] = json
            return MockResponse(payload={
                "id": "payment-id",
                "actions": [{"type": "REDIRECT_CUSTOMER", "value": "https://pay.example/redirect"}],
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
        payload = captured["payload"]
        self.assertEqual(payload["request_amount"], 50)
        self.assertEqual(payload["channel_properties"]["success_return_url"], "https://shop.example/checkout/success")
        self.assertEqual(payload["channel_properties"]["failure_return_url"], "https://shop.example/checkout/failed")


if __name__ == "__main__":
    unittest.main()
