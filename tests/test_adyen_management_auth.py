import unittest
from unittest.mock import MagicMock, patch

from app import create_app


class AdyenManagementAuthTests(unittest.TestCase):
    def create_client(self, token="secret-token"):
        app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_API_TOKEN": token,
        })
        return app.test_client()

    def test_management_routes_fail_closed_without_configured_token(self):
        client = self.create_client(token="")

        response = client.get("/api/adyen/stores")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"], "Adyen Management API token not configured")

    @patch("app.routes.api.requests.patch")
    @patch("app.routes.api.requests.get")
    def test_all_management_routes_reject_missing_token_before_proxying(self, mock_get, mock_patch):
        client = self.create_client()

        cases = [
            ("GET", "/api/adyen/stores", None),
            ("GET", "/api/adyen/stores/store-1", None),
            ("PATCH", "/api/adyen/stores/store-1", {"splitConfiguration": {"splitConfigurationId": "spc_1"}}),
            ("GET", "/api/adyen/splitConfigurations/spc_1", None),
            ("PATCH", "/api/adyen/splitConfigurations/spc_1/rules/rule-1", {"currency": "EUR"}),
            (
                "PATCH",
                "/api/adyen/splitConfigurations/spc_1/rules/rule-1/splitLogic/spl_1",
                {"commission": {"fixedAmount": 0}},
            ),
        ]

        for method, path, payload in cases:
            with self.subTest(method=method, path=path):
                response = client.open(path, method=method, json=payload)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.get_json()["error"], "Unauthorized")
        mock_get.assert_not_called()
        mock_patch.assert_not_called()

    @patch("app.routes.api.requests.patch")
    def test_management_write_route_rejects_bad_token_before_proxying(self, mock_patch):
        client = self.create_client()

        response = client.patch(
            "/api/adyen/stores/store-1",
            json={"splitConfiguration": {"splitConfigurationId": "spc_1"}},
            headers={"X-Adyen-Management-Api-Token": "wrong-token"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Unauthorized")
        mock_patch.assert_not_called()

    @patch("app.routes.api.requests.get")
    def test_management_route_accepts_bearer_token(self, mock_get):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = '{"data":[{"id":"store-1","reference":"store-ref","description":"Store"}]}'
        mock_response.json.return_value = {
            "data": [{"id": "store-1", "reference": "store-ref", "description": "Store"}],
            "itemsTotal": 1,
            "pagesTotal": 1,
        }
        mock_get.return_value = mock_response
        client = self.create_client()

        response = client.get(
            "/api/adyen/stores",
            headers={"Authorization": "Bearer secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["stores"][0]["id"], "store-1")
        mock_get.assert_called_once()


if __name__ == "__main__":
    unittest.main()
