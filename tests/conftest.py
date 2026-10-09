import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from gateway.config import settings

# Force SQLite test database file for test isolation
TEST_DB_FILE = "./test_trafficlens.db"
settings.DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

from gateway.models import Base
from gateway.database import get_db, init_db
from gateway.routing import ServiceRegistry
from gateway.rate_limit import FixedWindowRateLimiter
from gateway.main import app as gateway_app
from dashboard.api import app as dashboard_app

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass
    init_db()
    yield
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def dashboard_client():
    return TestClient(dashboard_app)

@pytest.fixture
def mock_registry():
    config = {
        "users": {
            "path_prefix": "/users",
            "instances": ["http://127.0.0.1:8001", "http://127.0.0.1:8002"]
        },
        "orders": {
            "path_prefix": "/orders",
            "instances": ["http://127.0.0.1:8003"]
        },
        "notifications": {
            "path_prefix": "/notify",
            "instances": ["http://127.0.0.1:8004"]
        }
    }
    return ServiceRegistry(registry_config=config)

@pytest.fixture
def rate_limiter():
    return FixedWindowRateLimiter(requests_limit=5, window_seconds=10)

@pytest.fixture
def gateway_client():
    return TestClient(gateway_app)
