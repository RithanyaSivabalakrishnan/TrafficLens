import pytest

def test_gateway_health_endpoint(gateway_client):
    res = gateway_client.get("/gateway/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "services" in data

def test_gateway_unknown_service(gateway_client):
    res = gateway_client.get("/gateway/invalid_service_foo/bar")
    assert res.status_code == 400
    data = res.json()
    assert data["outcome"] == "client_error"

def test_gateway_rate_limiting_trigger(gateway_client):
    # Send request to trigger client lookup
    res = gateway_client.get("/gateway/users/users")
    assert res.status_code in (200, 429, 502)
