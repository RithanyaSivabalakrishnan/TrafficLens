from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class GatewayErrorResponse(BaseModel):
    detail: str
    outcome: str
    request_id: str

class GatewayHealthServiceStatus(BaseModel):
    healthy_instances: int
    total_instances: int

class GatewayHealthResponse(BaseModel):
    status: str
    services: Dict[str, GatewayHealthServiceStatus]

# Dashboard API Schemas
class SummaryResponse(BaseModel):
    total_requests: int
    requests_per_second: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate_percent: float
    total_bandwidth_bytes: int
    window_start: str
    window_end: str

class LatencyPoint(BaseModel):
    timestamp: str
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float

class LatencyHistoryResponse(BaseModel):
    points: List[LatencyPoint]

class ThroughputPoint(BaseModel):
    timestamp: str
    requests_per_second: int

class ThroughputHistoryResponse(BaseModel):
    points: List[ThroughputPoint]

class TrafficDistributionItem(BaseModel):
    service: str
    endpoint: str
    request_count: int
    percentage: float

class TrafficDistributionResponse(BaseModel):
    services: List[TrafficDistributionItem]

class StatusCodeCategory(BaseModel):
    category: str
    count: int
    percentage: float

class StatusCodeResponse(BaseModel):
    categories: List[StatusCodeCategory]

class BackendHealthItem(BaseModel):
    service: str
    endpoint: str
    status: str  # Healthy, Slow, Down
    request_count: int
    average_latency_ms: float
    error_rate_percent: float
    active_connections: int
    rate_limited_count: int

class BackendHealthResponse(BaseModel):
    services: List[BackendHealthItem]

class BandwidthItem(BaseModel):
    service: str
    endpoint: str
    bytes: int
    megabytes: float
    percentage: float

class BandwidthResponse(BaseModel):
    services: List[BandwidthItem]

class ConnectionComparisonResponse(BaseModel):
    persistent_median_latency_ms: float
    new_connection_median_latency_ms: float
    difference_ms: float
    measurement_count: int
    last_measured_at: Optional[str] = None

class ExperimentDelayRequest(BaseModel):
    enabled: bool
    delay_ms: int = 300

class ExperimentStopServiceRequest(BaseModel):
    enabled: bool
