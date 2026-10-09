import asyncio
import time
from typing import Dict, Any
from fastapi import FastAPI, Request, Response, HTTPException

class SharedServiceState:
    def __init__(self):
        self.orders_delay_enabled: bool = False
        self.orders_delay_ms: int = 300
        self.notifications_stopped: bool = False

shared_state = SharedServiceState()

def create_service_app(service_name: str) -> FastAPI:
    app = FastAPI(title=f"TrafficLens {service_name.capitalize()} Microservice")

    @app.middleware("http")
    async def experiment_middleware(request: Request, call_next):
        # Handle experiment state for orders delay
        if service_name == "orders" and shared_state.orders_delay_enabled:
            await asyncio.sleep(shared_state.orders_delay_ms / 1000.0)
        
        # Handle experiment state for notification service failure
        if service_name == "notifications" and shared_state.notifications_stopped:
            if request.url.path == "/health":
                return Response(content='{"status": "error", "detail": "Service stopped by experiment"}', status_code=500, media_type="application/json")
            raise HTTPException(status_code=503, detail="Notification Service unavailable (Experiment Stop Active)")

        return await call_next(request)

    @app.get("/health")
    async def health_check():
        if service_name == "notifications" and shared_state.notifications_stopped:
            return Response(content='{"status": "down"}', status_code=500, media_type="application/json")
        return {"status": "ok", "service": service_name}

    @app.post("/_experiment/delay")
    async def toggle_delay(req: Dict[str, Any]):
        shared_state.orders_delay_enabled = req.get("enabled", False)
        if "delay_ms" in req:
            shared_state.orders_delay_ms = req["delay_ms"]
        return {"enabled": shared_state.orders_delay_enabled, "delay_ms": shared_state.orders_delay_ms}

    @app.post("/_experiment/stop-service")
    async def toggle_stop(req: Dict[str, Any]):
        shared_state.notifications_stopped = req.get("enabled", False)
        return {"enabled": shared_state.notifications_stopped}

    return app
