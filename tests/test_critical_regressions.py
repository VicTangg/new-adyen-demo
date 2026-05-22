import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app import create_app


class AdyenManagementWriteAuthTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "management-secret",
        })
        self.client = self.app.test_client()

    def test_management_patch_routes_reject_missing_token(self):
        endpoints = [
            "/api/adyen/stores/store-123",
            "/api/adyen/splitConfigurations/split-123/rules/rule-123",
            "/api/adyen/splitConfigurations/split-123/rules/rule-123/splitLogic/logic-123",
        ]

        with patch("app.routes.api.requests.patch") as patch_request:
            for endpoint in endpoints:
                with self.subTest(endpoint=endpoint):
                    response = self.client.patch(endpoint, json={"description": "mutated"})
                    self.assertEqual(401, response.status_code)

            patch_request.assert_not_called()

    def test_management_patch_accepts_configured_bearer_token(self):
        adyen_response = Mock(ok=True, text='{"id": "store-123"}')
        adyen_response.json.return_value = {"id": "store-123"}

        with patch("app.routes.api.requests.patch", return_value=adyen_response) as patch_request:
            response = self.client.patch(
                "/api/adyen/stores/store-123",
                json={"description": "updated"},
                headers={"Authorization": "Bearer management-secret"},
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual({"id": "store-123"}, response.get_json())
        patch_request.assert_called_once()


class ImageHostSafetyTest(unittest.TestCase):
    def make_client(self, image_delete_token="delete-secret"):
        app = create_app({
            "TESTING": True,
            "IMAGE_HOST_DELETE_TOKEN": image_delete_token,
        })
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        app.static_folder = temp_dir.name
        return app.test_client(), Path(temp_dir.name)

    def test_listing_over_quota_images_does_not_delete_files(self):
        client, static_dir = self.make_client()
        upload_dir = static_dir / "uploads_tmp"
        upload_dir.mkdir()
        existing_file = upload_dir / "old.png"
        existing_file.write_bytes(b"old-image")

        with patch("app.routes.api.IMAGE_HOST_MAX_BYTES", 1):
            response = client.get("/api/image-host/list")

        self.assertEqual(200, response.status_code)
        self.assertTrue(existing_file.exists())
        self.assertEqual(["old.png"], [img["filename"] for img in response.get_json()["images"]])

    def test_over_quota_upload_deletes_only_new_file(self):
        client, static_dir = self.make_client()
        upload_dir = static_dir / "uploads_tmp"
        upload_dir.mkdir()
        existing_file = upload_dir / "old.png"
        existing_file.write_bytes(b"existing")

        with patch("app.routes.api.IMAGE_HOST_MAX_BYTES", len(b"existing") + 1):
            response = client.post(
                "/api/image-host/upload",
                data={"image": (io.BytesIO(b"new-image"), "new.png", "image/png")},
                content_type="multipart/form-data",
            )

        self.assertEqual(507, response.status_code)
        self.assertTrue(existing_file.exists())
        self.assertEqual(["old.png"], sorted(path.name for path in upload_dir.iterdir()))

    def test_delete_all_requires_configured_token(self):
        client, static_dir = self.make_client()
        upload_dir = static_dir / "uploads_tmp"
        upload_dir.mkdir()
        existing_file = upload_dir / "old.png"
        existing_file.write_bytes(b"old-image")

        response = client.post("/api/image-host/delete-all")

        self.assertEqual(401, response.status_code)
        self.assertTrue(existing_file.exists())

    def test_delete_all_is_disabled_without_server_token(self):
        client, static_dir = self.make_client(image_delete_token="")
        upload_dir = static_dir / "uploads_tmp"
        upload_dir.mkdir()
        existing_file = upload_dir / "old.png"
        existing_file.write_bytes(b"old-image")

        response = client.post(
            "/api/image-host/delete-all",
            headers={"Authorization": "Bearer any-token"},
        )

        self.assertEqual(403, response.status_code)
        self.assertTrue(existing_file.exists())


if __name__ == "__main__":
    unittest.main()
