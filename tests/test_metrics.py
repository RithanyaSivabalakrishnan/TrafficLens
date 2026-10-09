import pytest
import asyncio
from gateway.metrics import MetricsCollector
from gateway.models import RequestMetric

@pytest.mark.asyncio
async def test_metrics_collector_queue(db_session):
    collector = MetricsCollector(max_queue_size=10)

    collector.record(
        request_id="req-123",
        client_ip="127.0.0.1",
        service="users",
        backend_url="http://127.0.0.1:8001",
        method="GET",
        path="/users",
        status_code=200,
        outcome="success",
        latency_ms=12.5,
        request_bytes=100,
        response_bytes=250
    )

    assert collector.queue.qsize() == 1

    # Save batch manually using session
    item = collector.queue.get_nowait()
    metric_obj = RequestMetric(**item)
    db_session.add(metric_obj)
    db_session.commit()

    saved = db_session.query(RequestMetric).filter_by(request_id="req-123").first()
    assert saved is not None
    assert saved.service == "users"
    assert saved.latency_ms == 12.5
    assert saved.request_bytes == 100
    assert saved.response_bytes == 250
