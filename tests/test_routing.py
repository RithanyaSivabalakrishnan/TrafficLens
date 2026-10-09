import pytest
from gateway.routing import ServiceRegistry, NoHealthyBackendError

@pytest.mark.asyncio
async def test_round_robin_alternation(mock_registry):
    # 'users' service has 8001 and 8002
    first = await mock_registry.select_next_backend("users")
    second = await mock_registry.select_next_backend("users")
    third = await mock_registry.select_next_backend("users")

    assert first == "http://127.0.0.1:8001"
    assert second == "http://127.0.0.1:8002"
    assert third == "http://127.0.0.1:8001"

@pytest.mark.asyncio
async def test_unhealthy_instance_exclusion(mock_registry):
    mock_registry.set_instance_health("http://127.0.0.1:8001", False)
    
    selected1 = await mock_registry.select_next_backend("users")
    selected2 = await mock_registry.select_next_backend("users")

    assert selected1 == "http://127.0.0.1:8002"
    assert selected2 == "http://127.0.0.1:8002"

@pytest.mark.asyncio
async def test_no_healthy_backend_exception(mock_registry):
    mock_registry.set_instance_health("http://127.0.0.1:8001", False)
    mock_registry.set_instance_health("http://127.0.0.1:8002", False)

    with pytest.raises(NoHealthyBackendError):
        await mock_registry.select_next_backend("users")

@pytest.mark.asyncio
async def test_unknown_service_exception(mock_registry):
    with pytest.raises(KeyError):
        await mock_registry.select_next_backend("unknown_service")
