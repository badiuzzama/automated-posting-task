"""DEV Community (Forem) - POST /api/articles (https://developers.forem.com/api/v1)"""
import httpx

from app.platforms.base import Platform, Published
from app.utils import strip_links


class DevToPlatform(Platform):
    name = "DEV Community"
    required_settings = ("devto_api_key",)

    async def publish(self, message: str, client: httpx.AsyncClient) -> Published:
        title = (strip_links(message) or "Update")[:80]
        resp = await client.post(
            "https://dev.to/api/articles",
            headers={
                "api-key": self.settings.devto_api_key,
                "Accept": "application/vnd.forem.api-v1+json",
            },
            json={"article": {"title": title, "body_markdown": message, "published": True, "tags": ["business"]}},
        )
        self.check(resp, "DEV post")
        return Published(url=resp.json()["url"])
