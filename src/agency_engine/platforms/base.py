"""Abstract base platform adapter and resilient HTTP client."""

from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from typing import Any

import httpx
import structlog

from agency_engine.domain.enums import PlatformName
from agency_engine.domain.exceptions import PlatformApiError
from agency_engine.domain.models import ActionProposal, PlatformResource, RawSnapshot

logger = structlog.get_logger()


class ResilientHttpClient:
    """Async HTTP client with concurrency limits, jittered backoff, and rate limit parsing."""

    def __init__(
        self,
        platform_name: str,
        concurrency: int = 3,
        max_retries: int = 4,
        timeout: float = 30.0,
    ) -> None:
        self.platform_name = platform_name
        self.semaphore = asyncio.Semaphore(concurrency)
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None
        self.timeout = timeout

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=self.timeout, write=20.0, pool=10.0)
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> httpx.Response:
        client = await self.get_client()

        for attempt in range(self.max_retries):
            try:
                async with self.semaphore:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=json_data,
                    )

                # Transient errors and rate-limiting
                if response.status_code in {429, 500, 502, 503, 504}:
                    retry_after_hdr = response.headers.get("Retry-After")
                    if retry_after_hdr and retry_after_hdr.isdigit():
                        backoff = float(retry_after_hdr)
                    else:
                        backoff = min(30.0, (2**attempt) + random.uniform(0.1, 0.9))

                    logger.warning(
                        "platform_http_throttled",
                        platform=self.platform_name,
                        status_code=response.status_code,
                        attempt=attempt + 1,
                        backoff=backoff,
                    )
                    if attempt == self.max_retries - 1:
                        raise PlatformApiError(
                            platform=self.platform_name,
                            status_code=response.status_code,
                            message=f"Retries exhausted. Raw: {response.text[:200]}",
                            is_transient=True,
                            retry_after=backoff,
                        )

                    await asyncio.sleep(backoff)
                    continue

                if response.is_error:
                    raise PlatformApiError(
                        platform=self.platform_name,
                        status_code=response.status_code,
                        message=response.text[:300],
                        is_transient=False,
                    )

                return response

            except httpx.RequestError as exc:
                if attempt == self.max_retries - 1:
                    raise PlatformApiError(
                        platform=self.platform_name,
                        status_code=None,
                        message=f"Network error: {str(exc)}",
                        is_transient=True,
                    ) from exc
                backoff = min(15.0, (2**attempt) + random.uniform(0.1, 0.5))
                await asyncio.sleep(backoff)

        raise PlatformApiError(platform=self.platform_name, message="Retry loop terminated")


class AdsPlatform(ABC):
    """Abstract base class for all advertising platforms."""

    platform_name: PlatformName
    api_version: str

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate current credentials and scopes against platform API."""

    @abstractmethod
    async def fetch_snapshots(
        self,
        account_id: str,
        date_preset: str = "yesterday",
        trace_id: str = "",
    ) -> RawSnapshot:
        """Fetch raw snapshot metrics without mutating data."""

    @abstractmethod
    async def get_resource(
        self,
        account_id: str,
        resource_id: str,
    ) -> PlatformResource | None:
        """Query live resource state (e.g., campaign status, daily budget)."""

    @abstractmethod
    async def preview_action(
        self,
        proposal: ActionProposal,
    ) -> dict[str, Any]:
        """Perform a dry-run / simulation of the proposed change."""

    @abstractmethod
    async def execute_action(
        self,
        proposal: ActionProposal,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Execute the mutating action if autonomy and consensus allow."""
