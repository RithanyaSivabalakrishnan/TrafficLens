import asyncio
import logging
from typing import Dict, List, Optional
from gateway.config import settings

logger = logging.getLogger("trafficlens.routing")

class NoHealthyBackendError(Exception):
    """Raised when no healthy backend instance is available for a service."""
    pass

class ServiceRegistry:
    def __init__(self, registry_config: Optional[Dict] = None):
        self.config = registry_config or settings.SERVICE_REGISTRY
        self._indices: Dict[str, int] = {svc: 0 for svc in self.config}
        self._lock = asyncio.Lock()
        
        # Instance health state map: url -> bool
        self._health_state: Dict[str, bool] = {}
        for svc, info in self.config.items():
            for inst in info["instances"]:
                self._health_state[inst] = True

    def set_instance_health(self, backend_url: str, is_healthy: bool):
        self._health_state[backend_url] = is_healthy

    def is_healthy(self, backend_url: str) -> bool:
        return self._health_state.get(backend_url, True)

    def get_service_instances(self, service_name: str) -> List[str]:
        if service_name not in self.config:
            return []
        return self.config[service_name]["instances"]

    def get_healthy_instances(self, service_name: str) -> List[str]:
        instances = self.get_service_instances(service_name)
        return [inst for inst in instances if self.is_healthy(inst)]

    async def select_next_backend(self, service_name: str) -> str:
        if service_name not in self.config:
            raise KeyError(f"Unknown service: {service_name}")

        async with self._lock:
            healthy_instances = self.get_healthy_instances(service_name)
            if not healthy_instances:
                raise NoHealthyBackendError(f"No healthy backend instance available for service '{service_name}'")

            current_idx = self._indices.get(service_name, 0)
            selected_instance = healthy_instances[current_idx % len(healthy_instances)]
            self._indices[service_name] = (current_idx + 1) % len(healthy_instances)

            return selected_instance

    def get_summary(self) -> Dict[str, Dict[str, int]]:
        summary = {}
        for svc in self.config:
            all_insts = self.get_service_instances(svc)
            healthy_insts = self.get_healthy_instances(svc)
            summary[svc] = {
                "healthy_instances": len(healthy_insts),
                "total_instances": len(all_insts)
            }
        return summary
