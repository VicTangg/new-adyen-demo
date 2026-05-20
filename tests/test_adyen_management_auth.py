import unittest
from unittest.mock import Mock, patch

from app import create_app


class AdyenManagementWriteAuthTest(unittest.TestCase):
    def create_client(self, token="write-token"):
        app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": token,
        })
        return app.test_client()

    @patch("app.routes.api.requests.patch")
    def test_management_patch_routes_reject_missing_token(self, mock_patch):
        client = self.create_client()
        paths = [
            "/api/adyen/stores/store-1",
            "/api/adyen/splitConfigurations/sc-1/rules/rule-1",
            "/api/adyen/splitConfigurations/sc-1/rules/rule-1/splitLogic/logic-1",
        ]

        for path in paths:
            with self.subTest(path=path):
                response = client.patch(path, json={"splitConfiguration": {"splitConfigurationId": "sc-2"}})
                self.assertEqual(response.status_code, 401)

        mock_patch.assert_not_called()

    @patch("app.routes.api.requests.patch")
    def test_management_patch_routes_are_disabled_without_configured_token(self, mock_patch):
        client = self.create_client(token="")

        response = client.patch(
            "/api/adyen/stores/store-1",
            json={"splitConfiguration": {"splitConfigurationId": "sc-2"}},
        )

        self.assertEqual(response.status_code, 403)
        mock_patch.assert_not_called()

    @patch("app.routes.api.requests.patch")
    def test_management_patch_accepts_bearer_token(self, mock_patch):
        client = self.create_client()
        mock_response = Mock(ok=True, text='{"id":"store-1"}')
        mock_response.json.return_value = {"id": "store-1"}
        mock_patch.return_value = mock_response

        response = client.patch(
            "/api/adyen/stores/store-1",
            headers={"Authorization": "Bearer write-token"},
            json={"splitConfiguration": {"splitConfigurationId": "sc-2"}},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "store-1"})
        mock_patch.assert_called_once()

    @patch("app.routes.api.requests.patch")
    def test_management_patch_accepts_write_token_header(self, mock_patch):
        client = self.create_client()
        mock_response = Mock(ok=True, text='{"ruleId":"rule-1"}')
        mock_response.json.return_value = {"ruleId": "rule-1"}
        mock_patch.return_value = mock_response

        response = client.patch(
            "/api/adyen/splitConfigurations/sc-1/rules/rule-1",
            headers={"X-Adyen-Management-Write-Token": "write-token"},
            json={"currency": "EUR", "paymentMethod": "ANY", "fundingSource": "ANY", "shopperInteraction": "ANY"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"ruleId": "rule-1"})
        mock_patch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
