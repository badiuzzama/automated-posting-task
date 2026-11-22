"""Base class shared by every platform integration."""
from __future__ import annotations

import abc
from dataclasses import dataclass

import httpx

from app.config import Settings


class PlatformError(Exception):
    """Raised by an integration when the platform rejects or cannot complete a post."""


@dataclass
class Published:
    url: str
    # True/False when the integration knows for sure; None -> verified with an anonymous GET.
    public: bool | None = None


class Platform(abc.ABC):
    #: Display name used in API responses.
    name: str = ""
    #: Names of Settings attributes that must be non-empty for this platform.
    required_settings: tuple[str, ...] = ()

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def missing_settings(self) -> list[str]:
        return [n.upper() for n in self.required_settings if not getattr(self.settings, n, None)]

    @abc.abstractmethod
    async def publish(self, message: str, client: httpx.AsyncClient) -> Published:
        """Publish ``message`` and return where it lives. Raise PlatformError on failure."""

    @staticmethod
    def check(response: httpx.Response, action: str) -> None:
        if response.is_success:
            return
        snippet = " ".join(response.text.split())[:200]
        raise PlatformError(f"{action} failed: HTTP {response.status_code} {snippet}".strip())
