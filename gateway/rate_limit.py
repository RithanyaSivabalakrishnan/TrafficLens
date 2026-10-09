import time
import asyncio
from typing import Dict, Tuple
from gateway.config import settings

class FixedWindowRateLimiter:
    def __init__(self, requests_limit: int = None, window_seconds: int = None):
        self.limit = requests_limit if requests_limit is not None else settings.RATE_LIMIT_REQUESTS
        self.window_seconds = window_seconds if window_seconds is not None else settings.RATE_LIMIT_WINDOW_SECONDS
        
        # Store mapping: client_ip -> (window_start_timestamp, request_count)
        self._counters: Dict[str, Tuple[int, int]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_ip: str) -> Tuple[bool, int, int]:
        """
        Check if request from client_ip is allowed.
        Returns: (is_allowed, current_count, seconds_until_reset)
        """
        now = int(time.time())
        current_window_start = (now // self.window_seconds) * self.window_seconds
        reset_in = (current_window_start + self.window_seconds) - now

        async with self._lock:
            if client_ip in self._counters:
                win_start, count = self._counters[client_ip]
                if win_start == current_window_start:
                    if count >= self.limit:
                        return False, count, reset_in
                    else:
                        self._counters[client_ip] = (current_window_start, count + 1)
                        return True, count + 1, reset_in
                else:
                    # New window reset
                    self._counters[client_ip] = (current_window_start, 1)
                    return True, 1, reset_in
            else:
                self._counters[client_ip] = (current_window_start, 1)
                return True, 1, reset_in

    async def reset(self):
        async with self._lock:
            self._counters.clear()
