import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.routes import api as api_module


class DummyResponse:
    ok = True
    status_code = 200
    text = '{"id": "resource-1"}'

    def json(self):
        return {"id": "resource-1"}


class CriticalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "management-secret",
            "IMAGE_HOST_DELETE_TOKEN": "delete-secret",
        })
        self.app.static_folder = self.tmpdir.name
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmpdir.cleanup()

    def image_dir(self):
        path = Path(self.app.static_folder) / api_module.IMAGE_HOST_DIR_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_delete_all_requires_token_and_preserves_files_when_denied(self):
        image_path = self.image_dir() / "keep.jpg"
        image_path.write_bytes(b"existing image")

        response = self.client.post("/api/image-host/delete-all")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(image_path.exists())

        response = self.client.post(
            "/api/image-host/delete-all",
            headers={"X-Image-Host-Delete-Token": "delete-secret"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(image_path.exists())

    def test_over_quota_upload_deletes_only_new_file(self):
        original_limit = api_module.IMAGE_HOST_MAX_BYTES
        api_module.IMAGE_HOST_MAX_BYTES = 10
        try:
            image_path = self.image_dir() / "existing.jpg"
            image_path.write_bytes(b"12345678")

            response = self.client.post(
                "/api/image-host/upload",
                data={"image": (io.BytesIO(b"abcde"), "new.jpg")},
                content_type="multipart/form-data",
            )

            self.assertEqual(response.status_code, 507)
            remaining = sorted(path.name for path in self.image_dir().iterdir())
            self.assertEqual(remaining, ["existing.jpg"])
            self.assertEqual(image_path.read_bytes(), b"12345678")
        finally:
            api_module.IMAGE_HOST_MAX_BYTES = original_limit

    def test_adyen_management_writes_require_token_before_external_patch(self):
        protected_routes = [
            "/api/adyen/stores/store-1",
            "/api/adyen/splitConfigurations/split-1/rules/rule-1",
            "/api/adyen/splitConfigurations/split-1/rules/rule-1/splitLogic/logic-1",
        ]

        with patch("app.routes.api.requests.patch") as mock_patch:
            for route in protected_routes:
                response = self.client.patch(route, json={"description": "changed"})
                self.assertEqual(response.status_code, 403, route)

            mock_patch.assert_not_called()

    def test_adyen_management_write_accepts_configured_bearer_token(self):
        with patch("app.routes.api.requests.patch", return_value=DummyResponse()) as mock_patch:
            response = self.client.patch(
                "/api/adyen/stores/store-1",
                json={"description": "changed"},
                headers={"Authorization": "Bearer management-secret"},
            )

            self.assertEqual(response.status_code, 200)
            mock_patch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
