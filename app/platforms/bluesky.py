"""Bluesky - AT Protocol: createSession + createRecord (https://docs.bsky.app/docs/api/)"""
from datetime import datetime, timezone

import httpx

from app.platforms.base import Platform, PlatformError, Published
from app.utils import find_links

XRPC = "https://bsky.social/xrpc"


class BlueskyPlatform(Platform):
    name = "Bluesky"
    required_settings = ("bluesky_handle", "bluesky_app_password")

    async def publish(self, message: str, client: httpx.AsyncClient) -> Published:
        s = self.settings
        login = await client.post(
            f"{XRPC}/com.atproto.server.createSession",
            json={"identifier": s.bluesky_handle, "password": s.bluesky_app_password},
        )
        self.check(login, "Bluesky login")
        session = login.json()

        record: dict = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        # Make the CTA a clickable link (facet offsets are UTF-8 byte positions).
        link = find_links(message)[0]
        start = message.find(link)
        if start >= 0:
            byte_start = len(message[:start].encode("utf-8"))
            record["facets"] = [
                {
                    "index": {"byteStart": byte_start, "byteEnd": byte_start + len(link.encode("utf-8"))},
                    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": link}],
                }
            ]

        resp = await client.post(
            f"{XRPC}/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {session['accessJwt']}"},
            json={"repo": session["did"], "collection": "app.bsky.feed.post", "record": record},
        )
        self.check(resp, "Bluesky post")
        uri = resp.json().get("uri", "")
        if not uri:
            raise PlatformError("Bluesky did not return a post URI")
        handle = session.get("handle") or s.bluesky_handle
        return Published(url=f"https://bsky.app/profile/{handle}/post/{uri.rsplit('/', 1)[-1]}")
