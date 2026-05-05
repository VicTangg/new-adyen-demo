import unittest
from unittest.mock import patch

from app import create_app


def make_client(admin_token=""):
    app = create_app({
        "TESTING": True,
        "ADYEN_API_KEY": "adyen-api-key",
        "ADYEN_MERCHANT_ACCOUNT": "merchant",
        "ADYEN_MANAGEMENT_ADMIN_TOKEN": admin_token,
    })
    return app.test_client()


class ManagementAuthTest(unittest.TestCase):
    def test_store_update_rejects_without_admin_token(self):
        client = make_client()

        with patch("app.routes.api.requests.patch") as patch_request:
            response = client.patch(
                "/api/adyen/stores/store-1",
                json={"splitConfiguration": {"splitConfigurationId": "sc-1"}},
            )

        self.assertEqual(response.status_code, 403)
        self.assertIn("disabled", response.get_json()["error"])
        patch_request.assert_not_called()

    def test_split_rule_update_rejects_wrong_admin_token(self):
        client = make_client(admin_token="correct-token")

        with patch("app.routes.api.requests.patch") as patch_request:
            response = client.patch(
                "/api/adyen/splitConfigurations/sc-1/rules/rule-1",
                headers={"X-Admin-Token": "wrong-token"},
                json={"currency": "EUR"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertIn("Unauthorized", response.get_json()["error"])
        patch_request.assert_not_called()

    def test_split_logic_update_allows_matching_admin_token(self):
        client = make_client(admin_token="correct-token")

        with patch("app.routes.api.requests.patch") as patch_request:
            patch_request.return_value.ok = True
            patch_request.return_value.text = '{"id":"updated"}'
            patch_request.return_value.json.return_value = {"id": "updated"}

            response = client.patch(
                "/api/adyen/splitConfigurations/sc-1/rules/rule-1/splitLogic/sl-1",
                headers={"X-Admin-Token": "correct-token"},
                json={"commission": {"fixedAmount": 10}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "updated"})
        patch_request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
