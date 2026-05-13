import unittest
from unittest.mock import patch

from app import create_app


class FakeResponse:
    ok = True
    status_code = 200
    text = "{}"

    def json(self):
        return {"id": "store-123", "reference": "store-ref"}


class AdyenManagementAuthTests(unittest.TestCase):
    def make_client(self, write_token=""):
        app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "test-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "test-merchant",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": write_token,
        })
        return app.test_client()

    def test_management_write_disabled_without_configured_token(self):
        client = self.make_client()

        with patch("app.routes.api.requests.patch") as mock_patch:
            response = client.patch(
                "/api/adyen/stores/store-123",
                json={"splitConfiguration": {"balanceAccountId": "BA123"}},
            )

        self.assertEqual(response.status_code, 403)
        mock_patch.assert_not_called()

    def test_management_write_rejects_missing_or_wrong_token(self):
        client = self.make_client("expected-token")

        for headers in ({}, {"Authorization": "Bearer wrong"}, {"X-Adyen-Management-Write-Token": "wrong"}):
            with self.subTest(headers=headers):
                with patch("app.routes.api.requests.patch") as mock_patch:
                    response = client.patch(
                        "/api/adyen/splitConfigurations/split-123/rules/rule-123",
                        json={"currency": "EUR", "fundingSource": "ANY", "paymentMethod": "ANY", "shopperInteraction": "Ecommerce"},
                        headers=headers,
                    )

                self.assertEqual(response.status_code, 401)
                mock_patch.assert_not_called()

    def test_management_write_accepts_valid_bearer_token(self):
        client = self.make_client("expected-token")

        with patch("app.routes.api.requests.patch", return_value=FakeResponse()) as mock_patch:
            response = client.patch(
                "/api/adyen/stores/store-123",
                json={"splitConfiguration": {"balanceAccountId": "BA123"}},
                headers={"Authorization": "Bearer expected-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["id"], "store-123")
        mock_patch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
