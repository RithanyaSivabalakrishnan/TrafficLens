import logging
import socket
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from gateway.config import settings
from gateway.models import Base

logger = logging.getLogger("trafficlens.database")

def is_host_reachable(host: str, port: int, timeout_sec: float = 0.5) -> bool:
    try:
        sock = socket.create_connection((host, port), timeout=timeout_sec)
        sock.close()
        return True
    except Exception:
        return False

def get_engine(db_url: str = None):
    url = db_url or settings.DATABASE_URL
    connect_args = {}
    
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return create_engine(url, connect_args=connect_args)
    elif "postgresql" in url:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432
        
        # Fast check if PostgreSQL port is open
        if not is_host_reachable(host, port, timeout_sec=0.3):
            logger.info(f"PostgreSQL server at {host}:{port} is unreachable. Switching to SQLite fallback.")
            return create_engine("sqlite:///./trafficlens_fallback.db", connect_args={"check_same_thread": False})
        
        connect_args["connect_timeout"] = 2
        return create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(target_engine=None):
    global engine, SessionLocal
    e = target_engine or engine
    try:
        Base.metadata.create_all(bind=e)
        logger.info("Database tables initialized successfully.")
    except Exception as ex:
        logger.warning(f"Could not connect to configured DATABASE_URL: {ex}")
        fallback_url = "sqlite:///./trafficlens_fallback.db"
        fallback_engine = get_engine(fallback_url)
        Base.metadata.create_all(bind=fallback_engine)
        engine = fallback_engine
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
