import pytest

def test_dashboard_api_summary_empty(dashboard_client):
    res = dashboard_client.get("/api/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_requests" in data
    assert "requests_per_second" in data
    assert "p50_latency_ms" in data
    assert data["total_requests"] == 0

def test_dashboard_api_latency_history(dashboard_client):
    res = dashboard_client.get("/api/latency-history")
    assert res.status_code == 200
    data = res.json()
    assert "points" in data
    assert len(data["points"]) == 60

def test_dashboard_api_throughput_history(dashboard_client):
    res = dashboard_client.get("/api/throughput-history")
    assert res.status_code == 200
    data = res.json()
    assert "points" in data
    assert len(data["points"]) == 60

def test_dashboard_api_traffic_distribution(dashboard_client):
    res = dashboard_client.get("/api/traffic-distribution")
    assert res.status_code == 200
    data = res.json()
    assert "services" in data

def test_dashboard_api_status_codes(dashboard_client):
    res = dashboard_client.get("/api/status-codes")
    assert res.status_code == 200
    data = res.json()
    assert "categories" in data
    assert len(data["categories"]) == 3

def test_dashboard_api_backend_health(dashboard_client):
    res = dashboard_client.get("/api/backend-health")
    assert res.status_code == 200
    data = res.json()
    assert "services" in data

def test_dashboard_api_bandwidth(dashboard_client):
    res = dashboard_client.get("/api/bandwidth")
    assert res.status_code == 200
    data = res.json()
    assert "services" in data

def test_dashboard_api_connection_comparison(dashboard_client):
    res = dashboard_client.get("/api/connection-comparison")
    assert res.status_code == 200
    data = res.json()
    assert "persistent_median_latency_ms" in data
    assert "new_connection_median_latency_ms" in data
