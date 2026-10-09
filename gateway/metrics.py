import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from gateway.config import settings
from gateway.database import SessionLocal
from gateway.models import RequestMetric

logger = logging.getLogger("trafficlens.metrics")

class MetricsCollector:
    def __init__(self, max_queue_size: int = 10000):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.flush_interval = settings.METRICS_FLUSH_INTERVAL_SECONDS
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._flusher_loop())
            logger.info("Metrics collector flusher started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            logger.info("Metrics collector flusher stopped.")

    def record(
        self,
        request_id: str,
        client_ip: str,
        service: str,
        backend_url: Optional[str],
        method: str,
        path: str,
        status_code: int,
        outcome: str,
        latency_ms: Optional[float],
        request_bytes: int = 0,
        response_bytes: int = 0,
        connection_reused: Optional[bool] = None
    ):
        data = {
            "request_id": request_id,
            "client_ip": client_ip,
            "service": service,
            "backend_url": backend_url,
            "method": method,
            "path": path,
            "status_code": status_code,
            "outcome": outcome,
            "latency_ms": latency_ms,
            "request_bytes": request_bytes,
            "response_bytes": response_bytes,
            "connection_reused": connection_reused,
            "created_at": datetime.now(timezone.utc)
        }
        try:
            self.queue.put_nowait(data)
        except asyncio.QueueFull:
            logger.warning("Metrics queue full; dropping metric record to preserve memory.")

    async def _flusher_loop(self):
        while self._running:
            await asyncio.sleep(self.flush_interval)
            await self.flush()

    async def flush(self):
        if self.queue.empty():
            return

        batch: List[Dict[str, Any]] = []
        while not self.queue.empty() and len(batch) < 1000:
            try:
                item = self.queue.get_nowait()
                batch.append(item)
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break

        if not batch:
            return

        # Perform DB insert in separate thread pool to keep asyncio loop free
        await asyncio.to_thread(self._save_batch, batch)

    def _save_batch(self, batch: List[Dict[str, Any]]):
        try:
            db = SessionLocal()
            try:
                objects = [RequestMetric(**item) for item in batch]
                db.bulk_save_objects(objects)
                db.commit()
            except Exception as ex:
                db.rollback()
                logger.error(f"Failed to persist metrics batch of {len(batch)} items to database: {ex}")
            finally:
                db.close()
        except Exception as db_ex:
            logger.error(f"Database session creation error during metrics flush: {db_ex}")
