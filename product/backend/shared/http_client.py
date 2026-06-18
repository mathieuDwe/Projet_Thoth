import asyncio
import random
import time
from typing import Optional
import httpx
from shared.config import get_settings


class ThothHttpClient:
    def __init__(self, service_name: str = "generic", client: Optional[httpx.AsyncClient] = None):
        self.settings = get_settings()
        self.service_name = service_name
        self._client = client
        self._owns_client = client is None
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or (self._owns_client and self._client.is_closed):
            proxy = self.settings.proxy_url or None
            transport = httpx.AsyncHTTPTransport(retries=self.settings.max_retries, proxy=proxy) if proxy else None
            self._client = httpx.AsyncClient(
                transport=transport,
                timeout=self.settings.max_timeout,
                follow_redirects=True,
                headers={"User-Agent": "ThothOSINT/1.0 (OSINT Platform)"},
            )
        return self._client

    async def _rate_limit(self):
        async with self._lock:
            elapsed = time.time() - self._last_request
            min_interval = 1.0 / self.settings.rate_limit_rps
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self._last_request = time.time()

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        retries: int = 0,
    ) -> httpx.Response:
        max_retries = retries or self.settings.max_retries
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                await self._rate_limit()
                client = await self._get_client()
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                )
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    await asyncio.sleep(retry_after + random.uniform(0.5, 2.0))
                    continue
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                if attempt < max_retries:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(wait)
                continue
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < max_retries:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(wait)
                    continue
                raise
        raise last_exception or RuntimeError(f"Request failed after {max_retries + 1} attempts")

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def close(self):
        if self._owns_client and self._client and not self._client.is_closed:
            await self._client.aclose()
