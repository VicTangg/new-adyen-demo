import unittest
from unittest.mock import Mock, patch

from app import create_app


class AdyenManagementAuthTest(unittest.TestCase):
    def create_client(self, write_token=""):
        app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "test-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "test-merchant",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": write_token,
        })
        return app.test_client()

    def assert_patch_forbidden_without_outbound_call(self, path, write_token=""):
        client = self.create_client(write_token=write_token)
        with patch("app.routes.api.requests.patch") as mocked_patch:
            response = client.patch(path, json={"splitConfiguration": {"splitConfigurationId": "spc_123"}})

        self.assertEqual(response.status_code, 403)
        mocked_patch.assert_not_called()

    def test_management_patch_routes_disabled_when_token_not_configured(self):
        paths = [
            "/api/adyen/stores/store_123",
            "/api/adyen/splitConfigurations/spc_123/rules/rule_123",
            "/api/adyen/splitConfigurations/spc_123/rules/rule_123/splitLogic/logic_123",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assert_patch_forbidden_without_outbound_call(path)

    def test_management_patch_routes_reject_missing_token_when_configured(self):
        paths = [
            "/api/adyen/stores/store_123",
            "/api/adyen/splitConfigurations/spc_123/rules/rule_123",
            "/api/adyen/splitConfigurations/spc_123/rules/rule_123/splitLogic/logic_123",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assert_patch_forbidden_without_outbound_call(path, write_token="secret-token")

    def test_store_patch_allows_matching_management_token(self):
        client = self.create_client(write_token="secret-token")
        adyen_response = Mock(ok=True, text='{"id":"store_123"}')
        adyen_response.json.return_value = {"id": "store_123"}

        with patch("app.routes.api.requests.patch", return_value=adyen_response) as mocked_patch:
            response = client.patch(
                "/api/adyen/stores/store_123",
                json={"splitConfiguration": {"splitConfigurationId": "spc_123"}},
                headers={"X-Management-Write-Token": "secret-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "store_123"})
        mocked_patch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
