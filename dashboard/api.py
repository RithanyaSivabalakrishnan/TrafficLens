import os
import argparse
import httpx
import uvicorn
from typing import Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from gateway.config import settings
from gateway.database import get_db, init_db
from gateway.schemas import (
    SummaryResponse, LatencyHistoryResponse, ThroughputHistoryResponse,
    TrafficDistributionResponse, StatusCodeResponse, BackendHealthResponse,
    BandwidthResponse, ConnectionComparisonResponse,
    ExperimentDelayRequest, ExperimentStopServiceRequest
)
from dashboard import queries

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="TrafficLens Dashboard API & Frontend", lifespan=lifespan)

# Ensure static files directory path
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_dashboard():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Dashboard index.html not found")
    return FileResponse(index_path)

@app.get("/api/summary", response_model=SummaryResponse)
async def api_summary(window_seconds: int = 60, db: Session = Depends(get_db)):
    window_seconds = min(max(1, window_seconds), 3600)
    return queries.get_summary(db, window_seconds=window_seconds)

@app.get("/api/latency-history", response_model=LatencyHistoryResponse)
async def api_latency_history(db: Session = Depends(get_db)):
    return queries.get_latency_history(db)

@app.get("/api/throughput-history", response_model=ThroughputHistoryResponse)
async def api_throughput_history(db: Session = Depends(get_db)):
    return queries.get_throughput_history(db)

@app.get("/api/traffic-distribution", response_model=TrafficDistributionResponse)
async def api_traffic_distribution(window_seconds: int = 60, db: Session = Depends(get_db)):
    return queries.get_traffic_distribution(db, window_seconds=window_seconds)

@app.get("/api/status-codes", response_model=StatusCodeResponse)
async def api_status_codes(window_seconds: int = 60, db: Session = Depends(get_db)):
    return queries.get_status_codes(db, window_seconds=window_seconds)

@app.get("/api/backend-health", response_model=BackendHealthResponse)
async def api_backend_health(db: Session = Depends(get_db)):
    return queries.get_backend_health(db)

@app.get("/api/bandwidth", response_model=BandwidthResponse)
async def api_bandwidth(window_seconds: int = 60, db: Session = Depends(get_db)):
    return queries.get_bandwidth(db, window_seconds=window_seconds)

@app.get("/api/connection-comparison", response_model=ConnectionComparisonResponse)
async def api_connection_comparison(db: Session = Depends(get_db)):
    return queries.get_connection_comparison(db)

# Development Experiment Endpoints
@app.post("/api/experiments/delay")
async def api_experiment_delay(payload: ExperimentDelayRequest):
    order_instances = settings.SERVICE_REGISTRY.get("orders", {}).get("instances", [])
    async with httpx.AsyncClient(timeout=2.0) as client:
        for inst in order_instances:
            try:
                await client.post(f"{inst.rstrip('/')}/_experiment/delay", json=payload.dict())
            except Exception:
                pass
    return {"enabled": payload.enabled, "delay_ms": payload.delay_ms}

@app.post("/api/experiments/stop-service")
async def api_experiment_stop(payload: ExperimentStopServiceRequest):
    notify_instances = settings.SERVICE_REGISTRY.get("notifications", {}).get("instances", [])
    async with httpx.AsyncClient(timeout=2.0) as client:
        for inst in notify_instances:
            try:
                await client.post(f"{inst.rstrip('/')}/_experiment/stop-service", json=payload.dict())
            except Exception:
                pass
    return {"enabled": payload.enabled}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TrafficLens Dashboard API Server")
    parser.add_argument("--host", type=str, default=settings.DASHBOARD_HOST, help="Host interface")
    parser.add_argument("--port", type=int, default=settings.DASHBOARD_PORT, help="Port to listen on")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
