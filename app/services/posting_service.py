"""Fan a message out to every platform concurrently, isolating failures."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable

import httpx

from app.platforms.base import Platform, PlatformError
from app.schemas import PlatformResult

logger = logging.getLogger("posting")


def _default_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=20.0, headers={"User-Agent": "automated-posting/1.0"})


class PostingService:
    def __init__(
        self,
        platforms: list[Platform],
        timeout: float = 30.0,
        client_factory: Callable[[], httpx.AsyncClient] = _default_client,
    ) -> None:
        self.platforms = platforms
        self.timeout = timeout
        self.client_factory = client_factory

    async def post_everywhere(self, message: str) -> list[PlatformResult]:
        async with self.client_factory() as client:
            tasks = [self._post_one(p, message, client) for p in self.platforms]
            return list(await asyncio.gather(*tasks))

    async def _post_one(self, platform: Platform, message: str, client: httpx.AsyncClient) -> PlatformResult:
        missing = platform.missing_settings()
        if missing:
            return self._failed(platform, f"Missing credentials: {', '.join(missing)}")
        try:
            published = await asyncio.wait_for(platform.publish(message, client), timeout=self.timeout)
        except PlatformError as exc:
            return self._failed(platform, str(exc))
        except asyncio.TimeoutError:
            return self._failed(platform, f"Timed out after {self.timeout:g}s")
        except httpx.HTTPError as exc:
            return self._failed(platform, f"Network error: {type(exc).__name__} {exc}".strip())
        except Exception as exc:  # never let one platform break the others
            logger.exception("Unexpected error posting to %s", platform.name)
            return self._failed(platform, f"Unexpected error: {type(exc).__name__}: {exc}")

        public = published.public
        if public is None:
            public = await self._is_public(client, published.url)
        now = datetime.now(timezone.utc)
        logger.info("%s: posted %s (public=%s)", platform.name, published.url, public)
        return PlatformResult(
            platform=platform.name,
            status="success",
            posted_url=published.url,
            public_access=public,
            date=now.date().isoformat(),
            time=now.strftime("%H:%M:%S"),
        )

    @staticmethod
    def _failed(platform: Platform, error: str) -> PlatformResult:
        logger.warning("%s: failed - %s", platform.name, error)
        return PlatformResult(platform=platform.name, status="failed", public_access=False, error=error)

    @staticmethod
    async def _is_public(client: httpx.AsyncClient, url: str) -> bool:
        """Anonymous GET (no credentials) to confirm the post can be opened by anyone."""
        try:
            resp = await client.get(url, follow_redirects=True, timeout=10.0)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
