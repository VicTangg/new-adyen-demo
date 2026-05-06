import json
import unittest
from unittest.mock import Mock, patch

from app import create_app


class AdyenManagementAuthTest(unittest.TestCase):
    def create_client(self, token="admin-token"):
        app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_API_TOKEN": token,
        })
        return app.test_client()

    def test_store_patch_requires_management_token(self):
        client = self.create_client()

        with patch("app.routes.api.requests.patch") as patch_request:
            response = client.patch(
                "/api/adyen/stores/store-123",
                json={"splitConfiguration": {"splitConfigurationId": "split-1"}},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Unauthorized")
        patch_request.assert_not_called()

    def test_store_patch_is_disabled_without_configured_token(self):
        client = self.create_client(token="")

        with patch("app.routes.api.requests.patch") as patch_request:
            response = client.patch(
                "/api/adyen/stores/store-123",
                json={"splitConfiguration": {"splitConfigurationId": "split-1"}},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "Adyen management updates are disabled")
        patch_request.assert_not_called()

    def test_store_patch_accepts_matching_management_token(self):
        client = self.create_client()
        adyen_response = Mock(ok=True, text=json.dumps({"id": "store-123"}))
        adyen_response.json.return_value = {"id": "store-123"}

        with patch("app.routes.api.requests.patch", return_value=adyen_response) as patch_request:
            response = client.patch(
                "/api/adyen/stores/store-123",
                headers={"X-Admin-Token": "admin-token"},
                json={"splitConfiguration": {"splitConfigurationId": "split-1"}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "store-123"})
        patch_request.assert_called_once()

    def test_split_logic_patch_accepts_bearer_token(self):
        client = self.create_client()
        adyen_response = Mock(ok=True, text=json.dumps({"splitLogicId": "logic-1"}))
        adyen_response.json.return_value = {"splitLogicId": "logic-1"}

        with patch("app.routes.api.requests.patch", return_value=adyen_response) as patch_request:
            response = client.patch(
                "/api/adyen/splitConfigurations/split-1/rules/rule-1/splitLogic/logic-1",
                headers={"Authorization": "Bearer admin-token"},
                json={"commission": {"fixedAmount": 0}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"splitLogicId": "logic-1"})
        patch_request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
