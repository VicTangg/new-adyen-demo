import unittest
from unittest.mock import patch

from app import create_app


class AdyenManagementWriteAuthTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "ADYEN_MERCHANT_ACCOUNT": "merchant",
            "ADYEN_API_KEY": "api-key",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "secret-token",
        })
        self.client = self.app.test_client()

    def _assert_requires_auth(self, path):
        with patch("app.routes.api.requests.patch") as mock_patch:
            response = self.client.patch(path, json={"description": "updated"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Adyen management write token required")
        mock_patch.assert_not_called()

    def test_store_update_requires_write_token(self):
        self._assert_requires_auth("/api/adyen/stores/store-1")

    def test_split_rule_update_requires_write_token(self):
        self._assert_requires_auth("/api/adyen/splitConfigurations/split-1/rules/rule-1")

    def test_split_logic_update_requires_write_token(self):
        self._assert_requires_auth(
            "/api/adyen/splitConfigurations/split-1/rules/rule-1/splitLogic/logic-1"
        )

    def test_invalid_write_token_is_rejected(self):
        with patch("app.routes.api.requests.patch") as mock_patch:
            response = self.client.patch(
                "/api/adyen/stores/store-1",
                headers={"X-Adyen-Management-Write-Token": "wrong-token"},
                json={"description": "updated"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "Invalid Adyen management write token")
        mock_patch.assert_not_called()

    def test_missing_configured_write_token_fails_closed(self):
        app = create_app({
            "TESTING": True,
            "ADYEN_MERCHANT_ACCOUNT": "merchant",
            "ADYEN_API_KEY": "api-key",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "",
        })
        client = app.test_client()

        with patch("app.routes.api.requests.patch") as mock_patch:
            response = client.patch(
                "/api/adyen/stores/store-1",
                headers={"Authorization": "Bearer any-token"},
                json={"description": "updated"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "Adyen management writes are not configured")
        mock_patch.assert_not_called()

    def test_valid_bearer_write_token_allows_forwarding(self):
        class MockResponse:
            ok = True
            text = "{}"
            status_code = 200

            def json(self):
                return {"id": "store-1", "description": "updated"}

        with patch("app.routes.api.requests.patch", return_value=MockResponse()) as mock_patch:
            response = self.client.patch(
                "/api/adyen/stores/store-1",
                headers={"Authorization": "Bearer secret-token"},
                json={"description": "updated"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["description"], "updated")
        mock_patch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
