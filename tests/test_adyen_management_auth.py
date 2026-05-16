import unittest
from unittest.mock import patch

from app import create_app


class FakeResponse:
    ok = True
    status_code = 200
    text = '{"id": "updated"}'

    def json(self):
        return {"id": "updated"}


class AdyenManagementWriteAuthTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "write-token",
        })
        self.client = self.app.test_client()

    def test_management_writes_reject_missing_token(self):
        endpoints = [
            "/api/adyen/stores/store-123",
            "/api/adyen/splitConfigurations/split-123/rules/rule-123",
            "/api/adyen/splitConfigurations/split-123/rules/rule-123/splitLogic/logic-123",
        ]

        with patch("app.routes.api.requests.patch") as mock_patch:
            for endpoint in endpoints:
                with self.subTest(endpoint=endpoint):
                    response = self.client.patch(endpoint, json={"description": "mutated"})
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.get_json()["error"], "Unauthorized")

            mock_patch.assert_not_called()

    def test_management_writes_reject_when_token_not_configured(self):
        app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "",
        })

        with patch("app.routes.api.requests.patch") as mock_patch:
            response = app.test_client().patch(
                "/api/adyen/stores/store-123",
                json={"description": "mutated"},
                headers={"X-Adyen-Management-Write-Token": "write-token"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"], "Adyen Management writes not configured")
        mock_patch.assert_not_called()

    def test_management_writes_accept_bearer_token(self):
        with patch("app.routes.api.requests.patch", return_value=FakeResponse()) as mock_patch:
            response = self.client.patch(
                "/api/adyen/stores/store-123",
                json={"description": "mutated"},
                headers={"Authorization": "Bearer write-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "updated"})
        mock_patch.assert_called_once()

    def test_management_writes_accept_custom_header_token(self):
        with patch("app.routes.api.requests.patch", return_value=FakeResponse()) as mock_patch:
            response = self.client.patch(
                "/api/adyen/splitConfigurations/split-123/rules/rule-123",
                json={"currency": "EUR"},
                headers={"X-Adyen-Management-Write-Token": "write-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "updated"})
        mock_patch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
