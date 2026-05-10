import unittest
from unittest.mock import Mock, patch

from app import create_app


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

    def test_management_writes_are_disabled_without_configured_token(self):
        client = self.create_client(token="")

        with patch("app.routes.api.requests.patch") as outbound_patch:
            response = client.patch(
                "/api/adyen/stores/store-1",
                json={"splitConfigurationId": "split-1"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"], "Adyen Management writes are not configured")
        outbound_patch.assert_not_called()

    def test_management_writes_reject_missing_or_wrong_token_before_forwarding(self):
        client = self.create_client()
        routes = [
            ("/api/adyen/stores/store-1", {"splitConfigurationId": "split-1"}),
            ("/api/adyen/splitConfigurations/split-1/rules/rule-1", {"currency": "EUR"}),
            (
                "/api/adyen/splitConfigurations/split-1/rules/rule-1/splitLogic/logic-1",
                {"commission": {"fixedAmount": 10}},
            ),
        ]

        for url, payload in routes:
            with self.subTest(url=url, token="missing"), patch("app.routes.api.requests.patch") as outbound_patch:
                response = client.patch(url, json=payload)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.get_json()["error"], "Forbidden")
                outbound_patch.assert_not_called()

            with self.subTest(url=url, token="wrong"), patch("app.routes.api.requests.patch") as outbound_patch:
                response = client.patch(
                    url,
                    json=payload,
                    headers={"Authorization": "Bearer wrong-token"},
                )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.get_json()["error"], "Forbidden")
                outbound_patch.assert_not_called()

    def test_management_write_allows_valid_bearer_token(self):
        client = self.create_client()
        outbound_response = Mock(ok=True, text='{"id":"store-1"}', status_code=200)
        outbound_response.json.return_value = {"id": "store-1"}

        with patch("app.routes.api.requests.patch", return_value=outbound_response) as outbound_patch:
            response = client.patch(
                "/api/adyen/stores/store-1",
                json={"splitConfigurationId": "split-1"},
                headers={"Authorization": "Bearer secret-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "store-1"})
        outbound_patch.assert_called_once()

    def test_management_write_allows_valid_custom_header(self):
        client = self.create_client()
        outbound_response = Mock(ok=True, text='{"id":"rule-1"}', status_code=200)
        outbound_response.json.return_value = {"id": "rule-1"}

        with patch("app.routes.api.requests.patch", return_value=outbound_response) as outbound_patch:
            response = client.patch(
                "/api/adyen/splitConfigurations/split-1/rules/rule-1",
                json={"currency": "EUR"},
                headers={"X-Adyen-Management-Write-Token": "secret-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "rule-1"})
        outbound_patch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
