import io
import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.routes import api


class ImageHostRegressionTests(unittest.TestCase):
    def setUp(self):
        self._original_max_bytes = api.IMAGE_HOST_MAX_BYTES
        self.tmp = tempfile.TemporaryDirectory()
        self.static_dir = Path(self.tmp.name) / "static"
        self.upload_dir = self.static_dir / api.IMAGE_HOST_DIR_NAME
        self.upload_dir.mkdir(parents=True)

        self.app = create_app({
            "TESTING": True,
            "IMAGE_HOST_DELETE_TOKEN": "delete-secret",
        })
        self.app.static_folder = str(self.static_dir)
        self.client = self.app.test_client()

    def tearDown(self):
        api.IMAGE_HOST_MAX_BYTES = self._original_max_bytes
        self.tmp.cleanup()

    def _write_upload(self, name, size):
        path = self.upload_dir / name
        path.write_bytes(b"x" * size)
        return path

    def test_listing_over_quota_does_not_delete_existing_images(self):
        api.IMAGE_HOST_MAX_BYTES = 10
        existing = self._write_upload("existing.png", 20)

        response = self.client.get("/api/image-host/list")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(existing.exists())
        self.assertEqual(response.get_json()["total_size_bytes"], 20)

    def test_over_quota_upload_deletes_only_new_file(self):
        api.IMAGE_HOST_MAX_BYTES = 2048
        existing = self._write_upload("existing.png", 1800)

        response = self.client.post(
            "/api/image-host/upload",
            data={"image": (io.BytesIO(b"y" * 400), "new.png", "image/png")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 507)
        self.assertTrue(existing.exists())
        self.assertEqual([p.name for p in self.upload_dir.iterdir()], ["existing.png"])

    def test_upload_rejects_request_larger_than_storage_cap(self):
        api.IMAGE_HOST_MAX_BYTES = 64

        response = self.client.post(
            "/api/image-host/upload",
            data={"image": (io.BytesIO(b"y" * 200), "too-large.png", "image/png")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(list(self.upload_dir.iterdir()), [])

    def test_delete_all_requires_shared_secret(self):
        existing = self._write_upload("existing.png", 20)

        forbidden = self.client.post("/api/image-host/delete-all")
        self.assertEqual(forbidden.status_code, 403)
        self.assertTrue(existing.exists())

        allowed = self.client.post(
            "/api/image-host/delete-all",
            headers={"X-Image-Host-Delete-Token": "delete-secret"},
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertFalse(existing.exists())


if __name__ == "__main__":
    unittest.main()
