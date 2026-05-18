import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app


class AdyenManagementAuthTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "admin-write-token",
        })
        self.client = self.app.test_client()

    def test_management_write_routes_reject_missing_token_before_patch(self):
        routes = [
            "/api/adyen/stores/store-id",
            "/api/adyen/splitConfigurations/split-id/rules/rule-id",
            "/api/adyen/splitConfigurations/split-id/rules/rule-id/splitLogic/logic-id",
        ]

        with patch("app.routes.api.requests.patch") as mock_patch:
            for route in routes:
                with self.subTest(route=route):
                    response = self.client.patch(route, json={"description": "changed"})

                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.get_json(), {"error": "Unauthorized"})

            mock_patch.assert_not_called()

    def test_management_write_routes_fail_closed_without_configured_token(self):
        app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "",
        })
        client = app.test_client()

        with patch("app.routes.api.requests.patch") as mock_patch:
            response = client.patch(
                "/api/adyen/stores/store-id",
                json={"description": "changed"},
                headers={"Authorization": "Bearer admin-write-token"},
            )

            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.get_json(), {"error": "Adyen Management writes are not configured"})
            mock_patch.assert_not_called()

    def test_bearer_token_allows_management_write(self):
        response_body = {"id": "store-id", "description": "updated"}
        upstream_response = SimpleNamespace(
            ok=True,
            text=json.dumps(response_body),
            json=lambda: response_body,
        )

        with patch("app.routes.api.requests.patch", return_value=upstream_response) as mock_patch:
            response = self.client.patch(
                "/api/adyen/stores/store-id",
                json={"description": "updated"},
                headers={"Authorization": "Bearer admin-write-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), response_body)
        mock_patch.assert_called_once()

    def test_custom_header_token_allows_management_write(self):
        response_body = {"ruleId": "rule-id", "currency": "EUR"}
        upstream_response = SimpleNamespace(
            ok=True,
            text=json.dumps(response_body),
            json=lambda: response_body,
        )

        with patch("app.routes.api.requests.patch", return_value=upstream_response) as mock_patch:
            response = self.client.patch(
                "/api/adyen/splitConfigurations/split-id/rules/rule-id",
                json={"currency": "EUR"},
                headers={"X-Adyen-Management-Write-Token": "admin-write-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), response_body)
        mock_patch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
