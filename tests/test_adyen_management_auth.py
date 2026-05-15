import unittest
from unittest.mock import patch

from app import create_app


class MockResponse:
    ok = True
    text = "{}"
    status_code = 200

    def json(self):
        return {"ok": True}


class AdyenManagementAuthTest(unittest.TestCase):
    def setUp(self):
        app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "management-token",
        })
        self.client = app.test_client()

    def test_management_writes_fail_closed_without_configured_token(self):
        app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "",
        })
        client = app.test_client()

        with patch("app.routes.api.requests.patch") as patch_request:
            response = client.patch("/api/adyen/stores/store-123", json={"splitConfiguration": {}})

        self.assertEqual(response.status_code, 403)
        patch_request.assert_not_called()

    def test_management_writes_require_token(self):
        routes = [
            ("/api/adyen/stores/store-123", {"splitConfiguration": {}}),
            ("/api/adyen/splitConfigurations/split-123/rules/rule-123", {"currency": "EUR"}),
            (
                "/api/adyen/splitConfigurations/split-123/rules/rule-123/splitLogic/logic-123",
                {"commission": {"fixedAmount": 1}},
            ),
        ]

        for path, payload in routes:
            with self.subTest(path=path):
                with patch("app.routes.api.requests.patch") as patch_request:
                    response = self.client.patch(path, json=payload)

                self.assertEqual(response.status_code, 401)
                patch_request.assert_not_called()

    def test_management_writes_accept_bearer_token(self):
        with patch("app.routes.api.requests.patch", return_value=MockResponse()) as patch_request:
            response = self.client.patch(
                "/api/adyen/stores/store-123",
                json={"splitConfiguration": {"splitConfigurationId": "split-123"}},
                headers={"Authorization": "Bearer management-token"},
            )

        self.assertEqual(response.status_code, 200)
        patch_request.assert_called_once()

    def test_management_writes_accept_management_header_token(self):
        with patch("app.routes.api.requests.patch", return_value=MockResponse()) as patch_request:
            response = self.client.patch(
                "/api/adyen/splitConfigurations/split-123/rules/rule-123",
                json={"currency": "EUR"},
                headers={"X-Adyen-Management-Write-Token": "management-token"},
            )

        self.assertEqual(response.status_code, 200)
        patch_request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
