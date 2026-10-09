# TrafficLens – Network-Aware API Gateway with Traffic Monitoring and Analytics

TrafficLens is a custom Python-based HTTP API Gateway, reverse proxy, and network telemetry system designed to demonstrate fundamental computer networking concepts: reverse proxying, round-robin load balancing, periodic backend health checking, per-client rate limiting, and real-time network telemetry storage in PostgreSQL visualized via an interactive web dashboard.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Problem Statement & Objectives](#problem-statement--objectives)
3. [Networking Concepts Demonstrated](#networking-concepts-demonstrated)
4. [System Architecture](#system-architecture)
5. [Folder Structure](#folder-structure)
6. [Technology Stack](#technology-stack)
7. [Configuration & Environment Variables](#configuration--environment-variables)
8. [Setup & Installation Instructions](#setup--installation-instructions)
9. [Running the Application](#running-the-application)
10. [Gateway & Dashboard API Reference](#gateway--dashboard-api-reference)
11. [Data Model](#data-model)
12. [TrafficLens Web Dashboard](#trafficlens-web-dashboard)
13. [Network Performance Experiments](#network-performance-experiments)
14. [Testing Suite](#testing-suite)
15. [Limitations & Known Constraints](#limitations--known-constraints)
16. [Troubleshooting](#troubleshooting)

---

## Project Overview
Modern web architectures rely on API Gateways to act as single entry points for client traffic. TrafficLens provides a lightweight, fully functional API Gateway built from scratch using Python, FastAPI, and `httpx`, avoiding off-the-shelf reverse proxy engines like Nginx or Envoy to provide direct code-level visibility into network traffic routing, state transition logic, and performance metrics persistence.

---

## Problem Statement & Objectives
- **Single Point of Entry**: Centralize request routing across microservices (`users`, `orders`, `notifications`).
- **Load Distribution**: Balance traffic evenly using healthy-instance Round-Robin load balancing.
- **Fault Tolerance**: Detect backend instance failures using active HTTP health checking and remove failing nodes automatically.
- **Abuse Prevention**: Enforce per-client fixed-window IP rate limiting (HTTP 429 Too Many Requests).
- **Network Telemetry**: Measure request latency (p50/p95/p99), throughput (RPS), application-layer bandwidth, and response status codes, persisting metrics to PostgreSQL.
- **Interactive Visualization**: Render live performance telemetry in a clean, responsive HTML/CSS/JS dashboard modeled after the TrafficLens visual specification.

---

## Networking Concepts Demonstrated
- **Transmission Control Protocol (TCP)**: HTTP request/response lifetime, connection pooling vs per-request TCP handshakes, latency reduction via persistent keep-alive connections.
- **Application Layer (HTTP)**: Forwarding HTTP methods, status codes, query strings, headers, and request/response payloads.
- **Reverse Proxying**: Decoupling clients from backend topology while obscuring internal service addresses.
- **Load Balancing**: Round-robin algorithm over dynamically updated healthy instance pools.
- **Active Health Checking**: Periodic probes to `/health` endpoints with failure/recovery state transitions.
- **Fixed-Window Rate Limiting**: Time-bucketed request accounting per client IP address.
- **Network Telemetry**: Measuring millisecond timing, payload sizes in bytes, status distributions, and percentile calculations.

---

## System Architecture

```
                                  +-----------------------+
                                  |  TrafficLens Frontend |
                                  |    (Web Dashboard)    |
                                  +-----------+-----------+
                                              | Polling GET /api/*
                                              v
+------------+  HTTP Requests   +-------------+-----------+  SQL Queries  +-----------------+
|   Client   | ---------------> |       API Gateway       | ------------> |   PostgreSQL    |
+------------+                  | & Dashboard Backend API |               |    Database     |
                                +-------------+-----------+               +-----------------+
                                              | Round-Robin Forwarding
                                              v
                               +--------------+--------------+
                               |    Backend Microservices    |
                               |  - User Service (8001/8002) |
                               |  - Order Service (8003)     |
                               |  - Notify Service (8004)    |
                               +-----------------------------+
```

---

## Folder Structure

```
trafficlens-gateway/
├── README.md                     # Comprehensive project documentation
├── PROJECT_MEMORY.md             # Implementation tracking and status
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment configuration template
├── .gitignore                    # Version control exclusions
├── docker-compose.yml            # Docker multi-container deployment
├── gateway/                      # API Gateway application core
│   ├── __init__.py
│   ├── main.py                   # FastAPI Gateway entry point
│   ├── config.py                 # Configuration loader and validator
│   ├── database.py               # PostgreSQL connection and engine
│   ├── models.py                 # SQLAlchemy database models
│   ├── schemas.py                # Pydantic schemas
│   ├── routing.py                # Service registry & round-robin router
│   ├── health.py                 # Active health checking engine
│   ├── rate_limit.py             # Fixed-window IP rate limiter
│   ├── proxy.py                  # HTTP reverse proxy forwarding engine
│   └── metrics.py                # Telemetry extraction & queue flusher
├── services/                     # Microservice implementations
│   ├── common.py                 # Shared backend service utilities
│   ├── user_service.py           # User microservice (8001, 8002)
│   ├── order_service.py          # Order microservice (8003)
│   └── notification_service.py   # Notification microservice (8004)
├── dashboard/                    # TrafficLens Web Dashboard
│   ├── api.py                    # FastAPI Dashboard API server
│   ├── queries.py                # PostgreSQL metric aggregate queries
│   └── static/                   # Frontend static assets
│       ├── index.html            # Dashboard layout
│       ├── styles.css            # Responsive styles & themes
│       └── app.js                # Live polling, charts, and interactivity
├── tests/                        # Comprehensive test suite
│   ├── conftest.py               # Pytest fixtures
│   ├── test_routing.py           # Routing logic unit tests
│   ├── test_health.py            # Health check state machine tests
│   ├── test_rate_limit.py        # Rate limiter unit tests
│   ├── test_proxy.py             # Reverse proxy unit tests
│   ├── test_metrics.py           # Telemetry collection tests
│   ├── test_dashboard_api.py     # Dashboard REST API tests
│   └── test_gateway_integration.py # E2E Integration tests
└── experiments/                  # Network performance benchmarking
    ├── README.md                 # Experiment instructions
    ├── benchmark.py              # Persistent vs new connection benchmark
    └── results/                  # Saved JSON benchmark outputs
```

---

## Technology Stack
- **Language**: Python 3.10+
- **API Framework**: FastAPI
- **ASGI Server**: Uvicorn
- **Async HTTP Client**: `httpx`
- **Database**: PostgreSQL (SQLAlchemy ORM + `psycopg[binary]`)
- **Dashboard Backend**: FastAPI
- **Dashboard Frontend**: HTML5, Vanilla CSS (CSS Grid, HSL custom properties), Vanilla JavaScript, SVG charting
- **Testing**: `pytest`, `pytest-asyncio`

---

## Configuration & Environment Variables

All configuration settings are loaded via `python-dotenv` from a `.env` file:

| Variable | Type | Default | Description |
|---|---|---|---|
| `GATEWAY_HOST` | string | `0.0.0.0` | Gateway interface address |
| `GATEWAY_PORT` | integer | `8000` | Gateway listening port |
| `DASHBOARD_HOST` | string | `0.0.0.0` | Dashboard interface address |
| `DASHBOARD_PORT` | integer | `8501` | Dashboard API and web port |
| `DATABASE_URL` | string | `postgresql+psycopg://postgres:postgres@localhost:5432/trafficlens` | PostgreSQL connection URL |
| `RATE_LIMIT_REQUESTS` | integer | `20` | Max requests per client window |
| `RATE_LIMIT_WINDOW_SECONDS` | integer | `60` | Fixed rate limit window in seconds |
| `HEALTH_CHECK_INTERVAL_SECONDS` | integer | `10` | Health check probe interval |
| `HEALTH_CHECK_TIMEOUT_SECONDS` | float | `2.0` | Health probe HTTP timeout |
| `UNHEALTHY_AFTER_FAILURES` | integer | `2` | Consecutive failures before Unhealthy |
| `HEALTHY_AFTER_SUCCESSES` | integer | `1` | Consecutive successes before Healthy |
| `UPSTREAM_TIMEOUT_SECONDS` | float | `5.0` | Gateway to backend HTTP timeout |
| `REUSE_UPSTREAM_CONNECTIONS` | boolean | `true` | Enable HTTP connection keep-alive |
| `METRICS_FLUSH_INTERVAL_SECONDS` | float | `1.0` | Background database flush interval |
| `DASHBOARD_REFRESH_INTERVAL_MS` | integer | `1000` | Frontend polling frequency |
| `DASHBOARD_TIME_WINDOW_SECONDS` | integer | `60` | Rolling metric analytics window |

---

## Setup & Installation Instructions

1. **Clone & Navigate**:
   ```bash
   cd TrafficLens
   ```

2. **Set up Virtual Environment**:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1   # On Windows PowerShell
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment File**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

---

## Running the Application

### Option A: Local Execution
1. **Start Microservices**:
   ```bash
   python -m services.user_service --port 8001
   python -m services.user_service --port 8002
   python -m services.order_service --port 8003
   python -m services.notification_service --port 8004
   ```

2. **Start API Gateway**:
   ```bash
   python -m gateway.main
   ```

3. **Start Dashboard API & Web UI**:
   ```bash
   python -m dashboard.api
   ```
   Open `http://localhost:8501` in your browser.

---

## Gateway & Dashboard API Reference

### Public Gateway Routes (`http://localhost:8000`)
- `ANY /gateway/{service}/{path:path}`: Forward request to selected service (`users`, `orders`, `notifications`).
- `GET /gateway/health`: Gateway health status and current healthy backend instances summary.

### Dashboard REST API (`http://localhost:8501`)
- `GET /`: Serves TrafficLens dashboard web page.
- `GET /api/summary`: Returns aggregate KPIs (Total Requests, RPS, p50, p95, p99, Error Rate, Bandwidth).
- `GET /api/latency-history`: Returns 60 one-second latency time buckets (p50, p95, p99).
- `GET /api/throughput-history`: Returns 60 one-second request-per-second buckets.
- `GET /api/traffic-distribution`: Returns request counts and percentages grouped by endpoint.
- `GET /api/status-codes`: Returns 2xx, 429, and 5xx status counts and percentages.
- `GET /api/backend-health`: Returns health state, average latency, and 429 counts per service instance.
- `GET /api/bandwidth`: Application-layer bandwidth usage per backend.
- `GET /api/connection-comparison`: Persistent vs new TCP connection latency benchmark metrics.
- `POST /api/experiments/delay`: Enables/disables artificial 300ms delay on Orders service.
- `POST /api/experiments/stop-service`: Simulates failure/down state for Notification service.

---

## Testing Suite

Run all automated unit, integration, and dashboard tests using `pytest`:

```bash
pytest -v
```

---

## Limitations & Known Constraints
- **Single-Process Rate Limiting**: Rate limit buckets are stored in-memory per gateway instance.
- **Application-Layer Bandwidth**: Bandwidth measurement tracks HTTP body and header payload byte sizes, excluding TCP/IP framing overhead.
- **Gateway-Observed Connections**: Active connection gauges track gateway in-flight request tasks.

---

## Troubleshooting
- **Database Connection Failed**: Ensure PostgreSQL is running on port 5432 and `DATABASE_URL` credentials are correct. Automated tests automatically fall back to SQLite when PostgreSQL is unavailable.
- **Backend Unreachable (HTTP 502)**: Verify microservices are running on ports 8001, 8002, 8003, and 8004.
- **Rate Limit Triggered (HTTP 429)**: Increase `RATE_LIMIT_REQUESTS` in `.env` if testing under high request volume.
