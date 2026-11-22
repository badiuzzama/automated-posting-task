"""Mastodon - POST /api/v1/statuses  (https://docs.joinmastodon.org/methods/statuses/)"""
import httpx

from app.platforms.base import Platform, Published


class MastodonPlatform(Platform):
    name = "Mastodon"
    required_settings = ("mastodon_instance_url", "mastodon_access_token")

    async def publish(self, message: str, client: httpx.AsyncClient) -> Published:
        s = self.settings
        base = s.mastodon_instance_url.rstrip("/")
        resp = await client.post(
            f"{base}/api/v1/statuses",
            headers={"Authorization": f"Bearer {s.mastodon_access_token}"},
            json={"status": message, "visibility": "public"},
        )
        self.check(resp, "Mastodon post")
        return Published(url=resp.json()["url"])
