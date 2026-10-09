import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Index, BigInteger
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

def utc_now():
    return datetime.now(timezone.utc)

class RequestMetric(Base):
    __tablename__ = "request_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(36), nullable=False, default=lambda: str(uuid.uuid4()))
    client_ip = Column(String(45), nullable=False)
    service = Column(String(64), nullable=False)
    backend_url = Column(String(512), nullable=True)
    method = Column(String(10), nullable=False)
    path = Column(String(512), nullable=False)
    status_code = Column(Integer, nullable=False)
    outcome = Column(String(32), nullable=False)
    latency_ms = Column(Float, nullable=True)
    request_bytes = Column(BigInteger, nullable=False, default=0)
    response_bytes = Column(BigInteger, nullable=False, default=0)
    connection_reused = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)

    __table_args__ = (
        Index("idx_req_service", "service"),
        Index("idx_req_outcome", "outcome"),
        Index("idx_req_service_created", "service", "created_at"),
    )

class BackendHealthEvent(Base):
    __tablename__ = "backend_health_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service = Column(String(64), nullable=False)
    backend_url = Column(String(512), nullable=False)
    previous_state = Column(String(16), nullable=False)
    new_state = Column(String(16), nullable=False)
    reason = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("idx_health_svc_created", "service", "created_at"),
        Index("idx_health_url_created", "backend_url", "created_at"),
    )

class ConnectionBenchmark(Base):
    __tablename__ = "connection_benchmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service = Column(String(64), nullable=False)
    connection_mode = Column(String(32), nullable=False)  # 'persistent' or 'new_connection'
    request_count = Column(Integer, nullable=False)
    median_latency_ms = Column(Float, nullable=False)
    average_latency_ms = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("idx_bench_svc_created", "service", "created_at"),
        Index("idx_bench_mode_created", "connection_mode", "created_at"),
    )
