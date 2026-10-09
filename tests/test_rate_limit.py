import pytest
import asyncio
from gateway.rate_limit import FixedWindowRateLimiter

@pytest.mark.asyncio
async def test_fixed_window_rate_limiter_threshold():
    limiter = FixedWindowRateLimiter(requests_limit=3, window_seconds=5)
    ip = "192.168.1.100"

    # First 3 requests should be allowed
    allowed1, count1, _ = await limiter.is_allowed(ip)
    allowed2, count2, _ = await limiter.is_allowed(ip)
    allowed3, count3, _ = await limiter.is_allowed(ip)

    assert allowed1 is True
    assert allowed2 is True
    assert allowed3 is True
    assert count3 == 3

    # 4th request should be rejected
    allowed4, count4, reset_in = await limiter.is_allowed(ip)
    assert allowed4 is False
    assert reset_in > 0

@pytest.mark.asyncio
async def test_rate_limiter_client_isolation():
    limiter = FixedWindowRateLimiter(requests_limit=2, window_seconds=5)
    ip_a = "10.0.0.1"
    ip_b = "10.0.0.2"

    await limiter.is_allowed(ip_a)
    await limiter.is_allowed(ip_a)
    allowed_a_3, _, _ = await limiter.is_allowed(ip_a)

    # ip_b should still be allowed
    allowed_b_1, _, _ = await limiter.is_allowed(ip_b)

    assert allowed_a_3 is False
    assert allowed_b_1 is True
