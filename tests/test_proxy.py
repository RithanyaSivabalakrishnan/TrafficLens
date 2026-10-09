import pytest
from gateway.proxy import HOP_BY_HOP_HEADERS, ReverseProxy

def test_hop_by_hop_header_filtering():
    headers = {
        "Host": "localhost:8000",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "User-Agent": "Pytest"
    }
    filtered = {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}

    assert "Host" not in filtered
    assert "Connection" not in filtered
    assert "Content-Type" in filtered
    assert "User-Agent" in filtered

@pytest.mark.asyncio
async def test_proxy_unreachable_backend_error():
    proxy = ReverseProxy(timeout_seconds=0.2, reuse_connections=False)
    
    class MockRequest:
        method = "GET"
        headers = {}
        url = type("URL", (), {"query": ""})()
        async def body(self):
            return b""

    req = MockRequest()
    resp, latency_ms, req_bytes, resp_bytes, outcome = await proxy.forward_request(
        request=req,
        backend_url="http://127.0.0.1:59999",
        target_path="health"
    )

    # Should return either 502 Bad Gateway or 504 Gateway Timeout
    assert resp.status_code in (502, 504)
    assert outcome in ("upstream_error", "upstream_timeout")
    assert latency_ms >= 0
