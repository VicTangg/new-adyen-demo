import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app


class _RawResult:
    def __init__(self, payload):
        self.raw_response = json.dumps(payload)


class _FakePaymentsApi:
    def __init__(self):
        self.payment_methods_payload = None
        self.payments_payloads = []

    def payment_methods(self, payload):
        self.payment_methods_payload = copy.deepcopy(payload)
        return _RawResult({"paymentMethods": []})

    def payments(self, payload):
        self.payments_payloads.append(copy.deepcopy(payload))
        return _RawResult({"resultCode": "Refused"})


class _FakeAdyenClient:
    def __init__(self):
        self.payments_api = _FakePaymentsApi()
        self.checkout = SimpleNamespace(payments_api=self.payments_api)


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.ok = status_code < 400
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class CriticalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "ADYEN_API_KEY": "adyen-key",
            "ADYEN_CLIENT_KEY": "adyen-client",
            "ADYEN_MERCHANT_ACCOUNT": "merchant-account",
            "ADYEN_MANAGEMENT_WRITE_TOKEN": "management-token",
            "IMAGE_HOST_DELETE_TOKEN": "delete-token",
            "XENDIT_SECRET_KEY": "xendit-secret",
        })
        self.app.static_folder = self.tmpdir.name
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _uploads_dir(self):
        path = Path(self.tmpdir.name) / "uploads_tmp"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_image_list_does_not_purge_existing_files_over_quota(self):
        existing = self._uploads_dir() / "existing.png"
        existing.write_bytes(b"x" * 16)

        with patch("app.routes.api.IMAGE_HOST_MAX_BYTES", 8):
            response = self.client.get("/api/image-host/list")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(existing.exists())
        self.assertEqual(response.get_json()["images"][0]["filename"], "existing.png")

    def test_over_quota_upload_rejects_new_file_without_deleting_existing_images(self):
        existing = self._uploads_dir() / "existing.png"
        existing.write_bytes(b"x" * 10)

        data = {
            "image": (io.BytesIO(b"\x89PNG\r\n" + b"y" * 10), "new.png"),
        }
        with patch("app.routes.api.IMAGE_HOST_MAX_BYTES", 12):
            response = self.client.post(
                "/api/image-host/upload",
                data=data,
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 507)
        self.assertTrue(existing.exists())
        self.assertEqual([p.name for p in self._uploads_dir().iterdir()], ["existing.png"])

    def test_image_delete_all_requires_token_before_removing_files(self):
        existing = self._uploads_dir() / "existing.png"
        existing.write_bytes(b"image")

        response = self.client.post("/api/image-host/delete-all")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(existing.exists())

        authorized = self.client.post(
            "/api/image-host/delete-all",
            headers={"X-Image-Host-Delete-Token": "delete-token"},
        )

        self.assertEqual(authorized.status_code, 200)
        self.assertFalse(existing.exists())

    def test_adyen_payment_methods_uses_server_cart_amount(self):
        fake = _FakeAdyenClient()

        with patch("app.routes.api.get_adyen_client", return_value=fake):
            response = self.client.post(
                "/api/adyen/paymentMethods",
                json={
                    "amount": {"value": 1, "currency": "USD"},
                    "channel": "iOS",
                    "countryCode": "NL",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            fake.payments_api.payment_methods_payload["amount"],
            {"value": 9498, "currency": "EUR"},
        )
        self.assertEqual(fake.payments_api.payment_methods_payload["channel"], "Web")

    def test_adyen_payments_overrides_browser_controlled_financial_fields(self):
        fake = _FakeAdyenClient()

        with patch("app.routes.api.get_adyen_client", return_value=fake):
            response = self.client.post(
                "/api/adyen/payments",
                json={
                    "amount": {"value": 1, "currency": "USD"},
                    "reference": "attacker-reference",
                    "returnUrl": "https://evil.example/steal",
                    "merchantAccount": "other-merchant",
                    "channel": "iOS",
                    "origin": "https://evil.example",
                    "paymentMethod": {"type": "scheme"},
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = fake.payments_api.payments_payloads[-1]
        self.assertEqual(payload["amount"], {"value": 9498, "currency": "EUR"})
        self.assertEqual(payload["merchantAccount"], "merchant-account")
        self.assertEqual(payload["channel"], "Web")
        self.assertTrue(payload["reference"].startswith("ref-"))
        self.assertNotEqual(payload["reference"], "attacker-reference")
        self.assertEqual(payload["returnUrl"], "http://localhost/checkout/return")
        self.assertEqual(payload["origin"], "http://localhost")

    def test_adyen_payments_applies_only_server_verifiable_alipay_discount(self):
        fake = _FakeAdyenClient()

        with patch("app.routes.api.get_adyen_client", return_value=fake):
            response = self.client.post(
                "/api/adyen/payments",
                json={
                    "amount": {"value": 1, "currency": "USD"},
                    "paymentMethod": {"type": "alipay"},
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            fake.payments_api.payments_payloads[-1]["amount"],
            {"value": 6649, "currency": "EUR"},
        )

    def test_adyen_management_writes_require_token(self):
        with patch("app.routes.api.requests.patch") as mocked_patch:
            response = self.client.patch(
                "/api/adyen/stores/store-1",
                json={"splitConfiguration": {"splitConfigurationId": "split-1"}},
            )

        self.assertEqual(response.status_code, 403)
        mocked_patch.assert_not_called()

        with patch("app.routes.api.requests.patch", return_value=_FakeResponse({"id": "store-1"})) as mocked_patch:
            authorized = self.client.patch(
                "/api/adyen/stores/store-1",
                json={"splitConfiguration": {"splitConfigurationId": "split-1"}},
                headers={"Authorization": "Bearer management-token"},
            )

        self.assertEqual(authorized.status_code, 200)
        mocked_patch.assert_called_once()

    def test_split_configuration_writes_require_token(self):
        endpoints = [
            "/api/adyen/splitConfigurations/split-1/rules/rule-1",
            "/api/adyen/splitConfigurations/split-1/rules/rule-1/splitLogic/logic-1",
        ]

        with patch("app.routes.api.requests.patch") as mocked_patch:
            for endpoint in endpoints:
                response = self.client.patch(endpoint, json={"currency": "EUR"})
                self.assertEqual(response.status_code, 403)

        mocked_patch.assert_not_called()

    def test_xendit_session_ignores_browser_controlled_amount_currency_country_and_origin(self):
        captured_payloads = []

        def fake_post(url, json=None, **kwargs):
            captured_payloads.append(copy.deepcopy(json))
            return _FakeResponse({"components_sdk_key": "sdk-key"})

        with patch("app.routes.api.requests.post", side_effect=fake_post):
            response = self.client.post(
                "/api/xendit/sessions",
                json={
                    "amount": 1,
                    "currency": "USD",
                    "country": "US",
                    "origin": "https://evil.example",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = captured_payloads[-1]
        self.assertEqual(payload["amount"], 9498)
        self.assertEqual(payload["currency"], "IDR")
        self.assertEqual(payload["country"], "ID")
        self.assertNotIn("https://evil.example", payload["components_configuration"]["origins"])

    def test_xendit_payment_request_ignores_browser_controlled_amount_and_return_urls(self):
        captured_payloads = []

        def fake_post(url, json=None, **kwargs):
            captured_payloads.append(copy.deepcopy(json))
            return _FakeResponse({
                "id": "payment-request-id",
                "actions": [{"type": "REDIRECT_CUSTOMER", "value": "https://xendit.example/pay"}],
            })

        with patch("app.routes.api.requests.post", side_effect=fake_post):
            response = self.client.post(
                "/api/xendit/payment-request",
                json={
                    "channel_code": "GRABPAY",
                    "amount": 1,
                    "success_return_url": "https://evil.example/success",
                    "failure_return_url": "https://evil.example/failure",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = captured_payloads[-1]
        self.assertEqual(payload["request_amount"], 50)
        self.assertEqual(payload["channel_properties"]["success_return_url"], "http://localhost/checkout/success")
        self.assertEqual(payload["channel_properties"]["failure_return_url"], "http://localhost/checkout/failed")

    def test_checkout_template_uses_live_sdk_host_and_fails_unknown_results_closed(self):
        app = create_app({
            "TESTING": True,
            "ADYEN_CLIENT_KEY": "adyen-client",
            "ADYEN_ENVIRONMENT": "live",
        })
        client = app.test_client()

        response = client.get("/checkout")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/6.33.0/adyen.js", body)
        self.assertIn("window.location.href = failedUrl;", body)
        self.assertNotIn("redirect to success to be safe", body)

    def test_env_example_does_not_contain_realistic_provider_secrets(self):
        sample = Path(".env.example").read_text()

        self.assertIn("ADYEN_API_KEY=your_adyen_api_key", sample)
        self.assertNotIn("AQEzhmfx", sample)
        self.assertNotIn("test_KNXVNDFXFNAUHADKEDYMCJBCCUUSYNCO", sample)


if __name__ == "__main__":
    unittest.main()
