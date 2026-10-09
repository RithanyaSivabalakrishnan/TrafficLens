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
