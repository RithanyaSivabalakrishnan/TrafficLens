import os
import sys
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class ConfigError(ValueError):
    """Raised when configuration validation fails."""
    pass

class Settings:
    def __init__(self):
        self.GATEWAY_HOST: str = os.getenv("GATEWAY_HOST", "0.0.0.0")
        self.GATEWAY_PORT: int = self._parse_int("GATEWAY_PORT", os.getenv("GATEWAY_PORT", "8000"), min_val=1, max_val=65535)

        self.DASHBOARD_HOST: str = os.getenv("DASHBOARD_HOST", "0.0.0.0")
        self.DASHBOARD_PORT: int = self._parse_int("DASHBOARD_PORT", os.getenv("DASHBOARD_PORT", "8501"), min_val=1, max_val=65535)

        db_url = os.getenv("DATABASE_URL")
        if not db_url or not db_url.strip():
            # Default fallback to postgresql+psycopg if not specified, but fail fast if explicitly invalid
            db_url = "postgresql+psycopg://postgres:postgres@localhost:5432/trafficlens"
        self.DATABASE_URL: str = db_url.strip()

        self.RATE_LIMIT_REQUESTS: int = self._parse_int("RATE_LIMIT_REQUESTS", os.getenv("RATE_LIMIT_REQUESTS", "20"), min_val=1)
        self.RATE_LIMIT_WINDOW_SECONDS: int = self._parse_int("RATE_LIMIT_WINDOW_SECONDS", os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"), min_val=1)

        self.HEALTH_CHECK_INTERVAL_SECONDS: float = self._parse_float("HEALTH_CHECK_INTERVAL_SECONDS", os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "10"), min_val=0.1)
        self.HEALTH_CHECK_TIMEOUT_SECONDS: float = self._parse_float("HEALTH_CHECK_TIMEOUT_SECONDS", os.getenv("HEALTH_CHECK_TIMEOUT_SECONDS", "2.0"), min_val=0.1)
        self.UNHEALTHY_AFTER_FAILURES: int = self._parse_int("UNHEALTHY_AFTER_FAILURES", os.getenv("UNHEALTHY_AFTER_FAILURES", "2"), min_val=1)
        self.HEALTHY_AFTER_SUCCESSES: int = self._parse_int("HEALTHY_AFTER_SUCCESSES", os.getenv("HEALTHY_AFTER_SUCCESSES", "1"), min_val=1)

        self.UPSTREAM_TIMEOUT_SECONDS: float = self._parse_float("UPSTREAM_TIMEOUT_SECONDS", os.getenv("UPSTREAM_TIMEOUT_SECONDS", "5.0"), min_val=0.1)
        self.REUSE_UPSTREAM_CONNECTIONS: bool = os.getenv("REUSE_UPSTREAM_CONNECTIONS", "true").lower() in ("true", "1", "yes", "on")

        self.METRICS_FLUSH_INTERVAL_SECONDS: float = self._parse_float("METRICS_FLUSH_INTERVAL_SECONDS", os.getenv("METRICS_FLUSH_INTERVAL_SECONDS", "1.0"), min_val=0.1)

        self.DASHBOARD_REFRESH_INTERVAL_MS: int = self._parse_int("DASHBOARD_REFRESH_INTERVAL_MS", os.getenv("DASHBOARD_REFRESH_INTERVAL_MS", "1000"), min_val=100)
        self.DASHBOARD_TIME_WINDOW_SECONDS: int = self._parse_int("DASHBOARD_TIME_WINDOW_SECONDS", os.getenv("DASHBOARD_TIME_WINDOW_SECONDS", "60"), min_val=1, max_val=3600)

        # Configure default service registry backend instances
        self.SERVICE_REGISTRY = {
            "users": {
                "path_prefix": "/users",
                "instances": [
                    "http://127.0.0.1:8001",
                    "http://127.0.0.1:8002"
                ]
            },
            "orders": {
                "path_prefix": "/orders",
                "instances": [
                    "http://127.0.0.1:8003"
                ]
            },
            "notifications": {
                "path_prefix": "/notify",
                "instances": [
                    "http://127.0.0.1:8004"
                ]
            }
        }

        self._validate()

    def _parse_int(self, var_name: str, raw_val: str, min_val: int = None, max_val: int = None) -> int:
        try:
            val = int(raw_val)
            if min_val is not None and val < min_val:
                raise ConfigError(f"Configuration key '{var_name}' must be >= {min_val}, got {val}")
            if max_val is not None and val > max_val:
                raise ConfigError(f"Configuration key '{var_name}' must be <= {max_val}, got {val}")
            return val
        except ValueError as e:
            if isinstance(e, ConfigError):
                raise
            raise ConfigError(f"Invalid integer for configuration key '{var_name}': '{raw_val}'")

    def _parse_float(self, var_name: str, raw_val: str, min_val: float = None) -> float:
        try:
            val = float(raw_val)
            if min_val is not None and val < min_val:
                raise ConfigError(f"Configuration key '{var_name}' must be >= {min_val}, got {val}")
            return val
        except ValueError as e:
            if isinstance(e, ConfigError):
                raise
            raise ConfigError(f"Invalid float for configuration key '{var_name}': '{raw_val}'")

    def _validate(self):
        # Validate URLs in service registry
        for service, info in self.SERVICE_REGISTRY.items():
            for inst in info["instances"]:
                parsed = urlparse(inst)
                if not parsed.scheme or not parsed.netloc:
                    raise ConfigError(f"Malformed backend URL '{inst}' for service '{service}'")

settings = Settings()
