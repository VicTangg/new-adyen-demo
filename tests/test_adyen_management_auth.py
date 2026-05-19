"""Regression tests for Adyen Management write proxy authorization."""
import unittest
from unittest.mock import patch

from app import create_app


class FakeResponse:
    ok = True
    status_code = 200
    text = "{}"

    def json(self):
        return {"id": "store-1"}


class AdyenManagementWriteAuthTest(unittest.TestCase):
    def create_client(self, token="secret-token"):
        app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": token,
        })
        return app.test_client()

    def write_routes(self):
        return [
            ("/api/adyen/stores/store-1", {"splitConfiguration": {"splitConfigurationId": "split-1"}}),
            ("/api/adyen/splitConfigurations/split-1/rules/rule-1", {"currency": "EUR"}),
            (
                "/api/adyen/splitConfigurations/split-1/rules/rule-1/splitLogic/logic-1",
                {"commission": {"fixedAmount": 10}},
            ),
        ]

    def test_management_write_disabled_without_configured_token(self):
        client = self.create_client(token="")

        for url, payload in self.write_routes():
            with self.subTest(url=url), patch("app.routes.api.requests.patch") as mock_patch:
                response = client.patch(url, json=payload)

            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.get_json()["error"], "Adyen management writes are not configured")
            mock_patch.assert_not_called()

    def test_management_write_rejects_missing_or_bad_token(self):
        client = self.create_client()

        for url, payload in self.write_routes():
            for headers in ({}, {"X-Adyen-Management-Write-Token": "wrong"}):
                with self.subTest(url=url, headers=headers), patch("app.routes.api.requests.patch") as mock_patch:
                    response = client.patch(url, json=payload, headers=headers)

                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.get_json()["error"], "Unauthorized")
                mock_patch.assert_not_called()

    def test_management_write_accepts_token_header(self):
        client = self.create_client()

        with patch("app.routes.api.requests.patch", return_value=FakeResponse()) as mock_patch:
            response = client.patch(
                "/api/adyen/stores/store-1",
                json={"splitConfiguration": {"splitConfigurationId": "split-1"}},
                headers={"X-Adyen-Management-Write-Token": "secret-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "store-1"})
        mock_patch.assert_called_once()

    def test_management_write_accepts_bearer_token(self):
        client = self.create_client()

        with patch("app.routes.api.requests.patch", return_value=FakeResponse()) as mock_patch:
            response = client.patch(
                "/api/adyen/splitConfigurations/split-1/rules/rule-1/splitLogic/logic-1",
                json={"commission": {"fixedAmount": 10}},
                headers={"Authorization": "Bearer secret-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "store-1"})
        mock_patch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
