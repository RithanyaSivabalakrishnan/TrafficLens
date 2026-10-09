import uuid
import logging
import argparse
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse

from gateway.config import settings
from gateway.database import init_db
from gateway.routing import ServiceRegistry, NoHealthyBackendError
from gateway.proxy import ReverseProxy
from gateway.health import HealthChecker
from gateway.rate_limit import FixedWindowRateLimiter
from gateway.metrics import MetricsCollector

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("trafficlens.gateway")

# Global component instances
service_registry = ServiceRegistry()
reverse_proxy = ReverseProxy()
health_checker = HealthChecker(service_registry)
rate_limiter = FixedWindowRateLimiter()
metrics_collector = MetricsCollector()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifecycle
    logger.info("Initializing Database...")
    init_db()
    
    logger.info("Starting background Health Checker and Metrics Collector...")
    health_checker.start()
    metrics_collector.start()
    
    yield

    # Shutdown lifecycle
    logger.info("Shutting down Gateway components...")
    health_checker.stop()
    metrics_collector.stop()
    await metrics_collector.flush()
    await reverse_proxy.close()
    logger.info("Gateway shutdown complete.")

app = FastAPI(
    title="TrafficLens Network-Aware API Gateway",
    description="Custom HTTP reverse-proxy gateway with health checks, rate limiting, and telemetry collection.",
    lifespan=lifespan
)

@app.get("/gateway/health")
async def gateway_health():
    summary = service_registry.get_summary()
    total_healthy = sum(info["healthy_instances"] for info in summary.values())
    total_instances = sum(info["total_instances"] for info in summary.values())
    
    status = "healthy" if total_healthy == total_instances else ("degraded" if total_healthy > 0 else "down")
    return {
        "status": status,
        "services": summary
    }

@app.api_route("/gateway/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def route_gateway_request(service: str, path: str, request: Request):
    req_id = str(uuid.uuid4())
    client_ip = request.client.host if request.client else "127.0.0.1"
    method = request.method

    # 1. Unknown service validation
    if service not in service_registry.config:
        metrics_collector.record(
            request_id=req_id,
            client_ip=client_ip,
            service=service,
            backend_url=None,
            method=method,
            path=f"/{path}",
            status_code=400,
            outcome="client_error",
            latency_ms=None
        )
        return JSONResponse(
            status_code=400,
            content={"detail": f"Unknown service '{service}'", "outcome": "client_error", "request_id": req_id}
        )

    # 2. Check Rate Limiter
    allowed, count, reset_in = await rate_limiter.is_allowed(client_ip)
    if not allowed:
        metrics_collector.record(
            request_id=req_id,
            client_ip=client_ip,
            service=service,
            backend_url=None,
            method=method,
            path=f"/{path}",
            status_code=429,
            outcome="rate_limited",
            latency_ms=None
        )
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(reset_in)},
            content={"detail": "Too Many Requests - Rate limit exceeded", "outcome": "rate_limited", "request_id": req_id}
        )

    # 3. Select Healthy Backend Instance
    try:
        backend_url = await service_registry.select_next_backend(service)
    except NoHealthyBackendError as ex:
        metrics_collector.record(
            request_id=req_id,
            client_ip=client_ip,
            service=service,
            backend_url=None,
            method=method,
            path=f"/{path}",
            status_code=502,
            outcome="no_healthy_backend",
            latency_ms=None
        )
        return JSONResponse(
            status_code=502,
            content={"detail": str(ex), "outcome": "no_healthy_backend", "request_id": req_id}
        )

    # 4. Forward Request via Reverse Proxy
    resp, latency_ms, req_bytes, resp_bytes, outcome = await reverse_proxy.forward_request(
        request=request,
        backend_url=backend_url,
        target_path=path
    )

    # 5. Record Request Metrics
    metrics_collector.record(
        request_id=req_id,
        client_ip=client_ip,
        service=service,
        backend_url=backend_url,
        method=method,
        path=f"/{path}",
        status_code=resp.status_code,
        outcome=outcome,
        latency_ms=latency_ms,
        request_bytes=req_bytes,
        response_bytes=resp_bytes,
        connection_reused=settings.REUSE_UPSTREAM_CONNECTIONS
    )

    return resp

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TrafficLens API Gateway")
    parser.add_argument("--host", type=str, default=settings.GATEWAY_HOST, help="Host interface")
    parser.add_argument("--port", type=int, default=settings.GATEWAY_PORT, help="Port to listen on")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
