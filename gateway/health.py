import asyncio
import logging
import httpx
from typing import Dict, Optional
from datetime import datetime, timezone
from gateway.config import settings
from gateway.routing import ServiceRegistry
from gateway.database import SessionLocal
from gateway.models import BackendHealthEvent

logger = logging.getLogger("trafficlens.health")

class HealthChecker:
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.interval = settings.HEALTH_CHECK_INTERVAL_SECONDS
        self.timeout = settings.HEALTH_CHECK_TIMEOUT_SECONDS
        self.unhealthy_threshold = settings.UNHEALTHY_AFTER_FAILURES
        self.healthy_threshold = settings.HEALTHY_AFTER_SUCCESSES

        # Tracking maps: url -> count
        self._consecutive_failures: Dict[str, int] = {}
        self._consecutive_successes: Dict[str, int] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info("Health check scheduler started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            logger.info("Health check scheduler stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await self.check_all_backends()
            except Exception as ex:
                logger.error(f"Error in health check loop: {ex}")
            await asyncio.sleep(self.interval)

    async def check_all_backends(self):
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for service, info in self.registry.config.items():
                for instance in info["instances"]:
                    await self._check_instance(client, service, instance)

    async def _check_instance(self, client: httpx.AsyncClient, service: str, instance: str):
        health_url = f"{instance.rstrip('/')}/health"
        is_success = False
        reason = ""

        try:
            resp = await client.get(health_url)
            if resp.status_code == 200:
                is_success = True
                reason = "HTTP 200 OK"
            else:
                reason = f"HTTP {resp.status_code}"
        except httpx.TimeoutException:
            reason = "Health check request timed out"
        except Exception as ex:
            reason = f"Connection error: {str(ex)}"

        currently_healthy = self.registry.is_healthy(instance)

        if is_success:
            self._consecutive_failures[instance] = 0
            succ_count = self._consecutive_successes.get(instance, 0) + 1
            self._consecutive_successes[instance] = succ_count

            if not currently_healthy and succ_count >= self.healthy_threshold:
                self.registry.set_instance_health(instance, True)
                self._record_event(service, instance, "unhealthy", "healthy", f"Recovered: {reason}")
                logger.info(f"Backend {instance} for service {service} marked HEALTHY")
        else:
            self._consecutive_successes[instance] = 0
            fail_count = self._consecutive_failures.get(instance, 0) + 1
            self._consecutive_failures[instance] = fail_count

            if currently_healthy and fail_count >= self.unhealthy_threshold:
                self.registry.set_instance_health(instance, False)
                self._record_event(service, instance, "healthy", "unhealthy", f"Failed: {reason}")
                logger.warning(f"Backend {instance} for service {service} marked UNHEALTHY")

    def _record_event(self, service: str, backend_url: str, prev_state: str, new_state: str, reason: str):
        try:
            db = SessionLocal()
            try:
                event = BackendHealthEvent(
                    service=service,
                    backend_url=backend_url,
                    previous_state=prev_state,
                    new_state=new_state,
                    reason=reason,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(event)
                db.commit()
            finally:
                db.close()
        except Exception as ex:
            logger.error(f"Failed to record health event in DB: {ex}")
