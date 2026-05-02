from app import create_app


BASE_CONFIG = {
    "TESTING": True,
    "ADYEN_API_KEY": "test-api-key",
    "ADYEN_MERCHANT_ACCOUNT": "test-merchant",
}


def make_client(extra_config=None):
    config = dict(BASE_CONFIG)
    if extra_config:
        config.update(extra_config)
    return create_app(config).test_client()


def test_management_write_routes_reject_when_token_not_configured():
    client = make_client()

    response = client.patch(
        "/api/adyen/stores/store-id",
        json={"splitConfiguration": {"balanceAccountId": "BA123"}},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Adyen Management writes not configured"


def test_management_write_routes_reject_wrong_token():
    client = make_client({"ADYEN_MANAGEMENT_WRITE_TOKEN": "expected-token"})

    response = client.patch(
        "/api/adyen/splitConfigurations/split-id/rules/rule-id",
        json={"currency": "EUR", "fundingSource": "ANY", "paymentMethod": "ANY", "shopperInteraction": "Ecommerce"},
        headers={"X-Adyen-Management-Write-Token": "wrong-token"},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Forbidden"


def test_management_write_routes_allow_configured_token_before_body_validation():
    client = make_client({"ADYEN_MANAGEMENT_WRITE_TOKEN": "expected-token"})

    response = client.patch(
        "/api/adyen/splitConfigurations/split-id/rules/rule-id/splitLogic/logic-id",
        json={},
        headers={"X-Adyen-Management-Write-Token": "expected-token"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Request body required"
