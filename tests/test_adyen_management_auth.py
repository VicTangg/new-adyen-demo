import unittest
from unittest.mock import patch

from app import create_app


class FakeResponse:
    ok = True
    status_code = 200
    text = '{"id":"store-1","reference":"store-ref"}'

    def json(self):
        return {"id": "store-1", "reference": "store-ref"}


class AdyenManagementAuthTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_ENVIRONMENT": "test",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "write-token",
        })
        self.client = self.app.test_client()

    def test_management_write_rejected_when_token_not_configured(self):
        app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-api-key",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "",
        })

        with patch("app.routes.api.requests.patch") as patch_request:
            response = app.test_client().patch(
                "/api/adyen/stores/store-1",
                json={"splitConfiguration": {"splitConfigurationId": "sc-1"}},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"], "Adyen management writes not configured")
        patch_request.assert_not_called()

    def test_management_write_endpoints_reject_missing_token(self):
        endpoints = [
            "/api/adyen/stores/store-1",
            "/api/adyen/splitConfigurations/sc-1/rules/rule-1",
            "/api/adyen/splitConfigurations/sc-1/rules/rule-1/splitLogic/logic-1",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint), patch("app.routes.api.requests.patch") as patch_request:
                response = self.client.patch(endpoint, json={"currency": "EUR"})

                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.get_json()["error"], "Unauthorized Adyen management write")
                patch_request.assert_not_called()

    def test_management_write_accepts_configured_header_token(self):
        with patch("app.routes.api.requests.patch", return_value=FakeResponse()) as patch_request:
            response = self.client.patch(
                "/api/adyen/stores/store-1",
                headers={"X-Adyen-Management-Write-Token": "write-token"},
                json={"splitConfiguration": {"splitConfigurationId": "sc-1"}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["id"], "store-1")
        patch_request.assert_called_once()

    def test_management_write_accepts_bearer_token(self):
        with patch("app.routes.api.requests.patch", return_value=FakeResponse()) as patch_request:
            response = self.client.patch(
                "/api/adyen/splitConfigurations/sc-1/rules/rule-1",
                headers={"Authorization": "Bearer write-token"},
                json={"currency": "EUR"},
            )

        self.assertEqual(response.status_code, 200)
        patch_request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
