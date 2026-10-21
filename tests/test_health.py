import pytest
from gateway.routing import ServiceRegistry
from gateway.health import HealthChecker

@pytest.mark.asyncio
async def test_health_check_threshold_transitions(mock_registry):
    checker = HealthChecker(mock_registry)
    inst = "http://127.0.0.1:8001"

    # Initially healthy
    assert mock_registry.is_healthy(inst) is True

    # Simulate 2 consecutive failures
    checker._consecutive_failures[inst] = 1
    # Check instance manually (simulating unreachable backend)
    # The registry state updates after UNHEALTHY_AFTER_FAILURES threshold (2)
    checker._consecutive_failures[inst] = 2
    mock_registry.set_instance_health(inst, False)

    assert mock_registry.is_healthy(inst) is False

    # Simulate recovery after 1 successful check
    checker._consecutive_successes[inst] = 1
    mock_registry.set_instance_health(inst, True)

    assert mock_registry.is_healthy(inst) is True

@pytest.mark.asyncio
async def test_recovery_from_db_unhealthy_state(mock_registry, db_session):
    from datetime import datetime, timezone
    from gateway.models import BackendHealthEvent

    checker = HealthChecker(mock_registry)
    inst = "http://127.0.0.1:8004"

    # Seed an unhealthy event in DB as if a previous failure occurred
    db_session.add(BackendHealthEvent(
        service="notifications",
        backend_url=inst,
        previous_state="healthy",
        new_state="unhealthy",
        reason="Failed: HTTP 500",
        created_at=datetime.now(timezone.utc)
    ))
    db_session.commit()

    assert checker._is_last_event_unhealthy(inst) is True

    # Even if mock_registry starts fresh with in-memory healthy=True
    assert mock_registry.is_healthy(inst) is True

    # Now simulate a successful health check after backend restart
    class DummyClient:
        async def get(self, url):
            class DummyResp:
                status_code = 200
            return DummyResp()

    await checker._check_instance(DummyClient(), "notifications", inst)

    # Registry is healthy and recovery event was persisted to DB!
    assert mock_registry.is_healthy(inst) is True
    assert checker._is_last_event_unhealthy(inst) is False
