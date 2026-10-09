import time
import logging
import httpx
from typing import Tuple, Dict, Any, Optional
from fastapi import Request, Response
from gateway.config import settings

logger = logging.getLogger("trafficlens.proxy")

# Standard HTTP hop-by-hop headers to strip when forwarding
HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host"
}

class ReverseProxy:
    def __init__(self, timeout_seconds: Optional[float] = None, reuse_connections: Optional[bool] = None):
        self.timeout = timeout_seconds if timeout_seconds is not None else settings.UPSTREAM_TIMEOUT_SECONDS
        self.reuse_connections = reuse_connections if reuse_connections is not None else settings.REUSE_UPSTREAM_CONNECTIONS
        
        # Shared client for connection pooling when reuse is enabled
        self._shared_client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self.reuse_connections:
            if self._shared_client is None or self._shared_client.is_closed:
                self._shared_client = httpx.AsyncClient(timeout=self.timeout)
            return self._shared_client
        else:
            return httpx.AsyncClient(timeout=self.timeout)

    async def close(self):
        if self._shared_client and not self._shared_client.is_closed:
            await self._shared_client.aclose()

    async def forward_request(
        self,
        request: Request,
        backend_url: str,
        target_path: str
    ) -> Tuple[Response, float, int, int, str]:
        """
        Forward client request to backend_url + target_path.
        Returns: (fastapi_response, latency_ms, request_bytes, response_bytes, outcome)
        """
        # Construct target URL
        full_target_url = f"{backend_url.rstrip('/')}/{target_path.lstrip('/')}"
        if request.url.query:
            full_target_url += f"?{request.url.query}"

        method = request.method
        body = await request.body()
        request_bytes = len(body)

        # Prepare headers
        forward_headers = {}
        for k, v in request.headers.items():
            if k.lower() not in HOP_BY_HOP_HEADERS:
                forward_headers[k] = v

        start_time = time.monotonic()
        client = await self.get_client()

        try:
            if self.reuse_connections:
                resp = await client.request(
                    method=method,
                    url=full_target_url,
                    headers=forward_headers,
                    content=body
                )
            else:
                async with client as temp_client:
                    resp = await temp_client.request(
                        method=method,
                        url=full_target_url,
                        headers=forward_headers,
                        content=body
                    )

            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            response_bytes = len(resp.content)

            # Filter response headers
            res_headers = {}
            for k, v in resp.headers.items():
                if k.lower() not in HOP_BY_HOP_HEADERS:
                    res_headers[k] = v

            fastapi_resp = Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=res_headers,
                media_type=resp.headers.get("content-type")
            )

            outcome = "success"
            return fastapi_resp, elapsed_ms, request_bytes, response_bytes, outcome

        except httpx.TimeoutException:
            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            logger.warning(f"Upstream timeout for {full_target_url}")
            err_resp = Response(
                content='{"detail": "Gateway Timeout", "outcome": "upstream_timeout"}',
                status_code=504,
                media_type="application/json"
            )
            return err_resp, elapsed_ms, request_bytes, 0, "upstream_timeout"

        except (httpx.ConnectError, httpx.RequestError) as ex:
            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            logger.warning(f"Upstream connection error for {full_target_url}: {ex}")
            err_resp = Response(
                content='{"detail": "Bad Gateway - Upstream service connection failed", "outcome": "upstream_error"}',
                status_code=502,
                media_type="application/json"
            )
            return err_resp, elapsed_ms, request_bytes, 0, "upstream_error"
