import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.routes import api as api_module


class CriticalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.static_dir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "management-token",
            "IMAGE_HOST_DELETE_TOKEN": "delete-token",
        })
        self.app.static_folder = self.static_dir.name
        self.client = self.app.test_client()

    def tearDown(self):
        self.static_dir.cleanup()

    def image_dir(self):
        path = Path(self.static_dir.name) / api_module.IMAGE_HOST_DIR_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_image_delete_all_requires_token_before_deleting_files(self):
        existing = self.image_dir() / "keep.png"
        existing.write_bytes(b"existing")

        response = self.client.post("/api/image-host/delete-all")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(existing.exists())

    def test_image_delete_all_accepts_configured_token(self):
        existing = self.image_dir() / "delete-me.png"
        existing.write_bytes(b"existing")

        response = self.client.post(
            "/api/image-host/delete-all",
            headers={"X-Image-Host-Delete-Token": "delete-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(existing.exists())

    def test_over_quota_upload_rejects_new_file_without_purging_existing_images(self):
        existing = self.image_dir() / "existing.png"
        existing.write_bytes(b"keep")
        old_limit = api_module.IMAGE_HOST_MAX_BYTES
        api_module.IMAGE_HOST_MAX_BYTES = len(b"keep") + len(b"new-file") - 1
        try:
            response = self.client.post(
                "/api/image-host/upload",
                data={"image": (io.BytesIO(b"new-file"), "new.png")},
                content_type="multipart/form-data",
            )
        finally:
            api_module.IMAGE_HOST_MAX_BYTES = old_limit

        self.assertEqual(response.status_code, 507)
        self.assertTrue(existing.exists())
        self.assertEqual(["existing.png"], sorted(path.name for path in self.image_dir().iterdir()))

    def test_adyen_management_write_routes_require_token_before_proxying(self):
        routes = [
            "/api/adyen/stores/store-id",
            "/api/adyen/splitConfigurations/split-id/rules/rule-id",
            "/api/adyen/splitConfigurations/split-id/rules/rule-id/splitLogic/logic-id",
        ]
        for route in routes:
            with self.subTest(route=route), patch("app.routes.api.requests.patch") as proxied_patch:
                response = self.client.patch(route, json={"description": "changed"})
                self.assertEqual(response.status_code, 403)
                proxied_patch.assert_not_called()

    def test_adyen_management_write_routes_accept_configured_token(self):
        class FakeResponse:
            ok = True
            status_code = 200
            text = "{}"

            def json(self):
                return {"id": "store-id"}

        with patch("app.routes.api.requests.patch", return_value=FakeResponse()) as proxied_patch:
            response = self.client.patch(
                "/api/adyen/stores/store-id",
                json={"description": "changed"},
                headers={"Authorization": "Bearer management-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "store-id"})
        proxied_patch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
