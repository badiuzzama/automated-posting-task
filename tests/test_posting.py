import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, get_posting_service
from app.platforms.base import Platform, PlatformError, Published
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.mastodon import MastodonPlatform
from app.services.posting_service import PostingService

VALID = "Check out our latest business platform and grow your online visibility. https://example.com"


# ---------- fake platforms ----------
class OkPlatform(Platform):
    name = "OK"

    async def publish(self, message, client):
        return Published(url="https://ok.example/post/1", public=True)


class BoomPlatform(Platform):
    name = "Boom"

    async def publish(self, message, client):
        raise PlatformError("Authentication failed")


class CrashPlatform(Platform):
    name = "Crash"

    async def publish(self, message, client):
        raise RuntimeError("kaboom")


class NeedsKeyPlatform(Platform):
    name = "NeedsKey"
    required_settings = ("devto_api_key",)

    async def publish(self, message, client):  # pragma: no cover
        raise AssertionError("must not be called")


def make_service(platforms):
    return PostingService(
        platforms,
        timeout=2,
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))),
    )


@pytest.fixture
def client():
    settings = Settings(_env_file=None)
    svc = make_service([OkPlatform(settings), BoomPlatform(settings)])
    app.dependency_overrides[get_posting_service] = lambda: svc
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------- endpoint & validation ----------
def test_valid_request_returns_per_platform_results(client):
    r = client.post("/posting", json={"message": VALID})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    ok, failed = body["results"]
    assert ok["status"] == "success" and ok["posted_url"] and ok["public_access"] is True
    assert ok["date"] and ok["time"] and ok["error"] is None
    assert failed["status"] == "failed" and failed["error"] == "Authentication failed"
    assert failed["posted_url"] is None and failed["date"] is None


@pytest.mark.parametrize(
    "message, fragment",
    [
        ("x" * 201, "200"),
        ("Hello world with no link at all", "none was found"),
        ("Two links https://a.com and https://b.com", "2 were found"),
        ("Bad domain https://invalid", "invalid domain"),
        ("No scheme www.example.com", "http://"),
        ("Wrong scheme ftp://example.com/file", "http://"),
        ("Bad port https://example.com:99999", "invalid port"),
        ("   ", "at least 1"),
    ],
)
def test_invalid_messages_rejected(client, message, fragment):
    r = client.post("/posting", json={"message": message})
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False
    assert fragment in body["errors"][0]["message"]
    assert body["errors"][0]["field"] == "message"


def test_missing_field_and_wrong_type(client):
    assert client.post("/posting", json={}).status_code == 422
    assert client.post("/posting", json={"message": 123}).status_code == 422


def test_exactly_200_chars_is_allowed(client):
    link = "https://example.com"
    msg = "a" * (200 - len(link) - 1) + " " + link
    assert len(msg) == 200
    assert client.post("/posting", json={"message": msg}).status_code == 200


def test_trailing_punctuation_not_part_of_link(client):
    assert client.post("/posting", json={"message": "Visit (https://example.com)."}).status_code == 200


# ---------- service: isolation of failures ----------
def test_one_failure_does_not_stop_others():
    settings = Settings(_env_file=None, devto_api_key=None)
    svc = make_service(
        [BoomPlatform(settings), CrashPlatform(settings), NeedsKeyPlatform(settings), OkPlatform(settings)]
    )
    results = asyncio.run(svc.post_everywhere(VALID))
    by_name = {r.platform: r for r in results}
    assert by_name["OK"].status == "success"
    assert by_name["Boom"].error == "Authentication failed"
    assert "kaboom" in by_name["Crash"].error
    assert by_name["NeedsKey"].error == "Missing credentials: DEVTO_API_KEY"


def test_all_failed_gives_success_false():
    settings = Settings(_env_file=None)
    svc = make_service([BoomPlatform(settings)])
    app.dependency_overrides[get_posting_service] = lambda: svc
    try:
        body = TestClient(app).post("/posting", json={"message": VALID}).json()
    finally:
        app.dependency_overrides.clear()
    assert body["success"] is False


def test_timeout_is_reported():
    class Slow(Platform):
        name = "Slow"

        async def publish(self, message, client):
            await asyncio.sleep(5)

    svc = PostingService([Slow(Settings(_env_file=None))], timeout=0.05,
                         client_factory=lambda: httpx.AsyncClient())
    (res,) = asyncio.run(svc.post_everywhere(VALID))
    assert res.status == "failed" and "Timed out" in res.error


def test_public_check_marks_unreachable_url_as_not_public():
    class Plain(Platform):
        name = "Plain"

        async def publish(self, message, client):
            return Published(url="https://plain.example/p/1")  # public=None -> verified

    def handler(request):
        return httpx.Response(404)

    svc = PostingService([Plain(Settings(_env_file=None))],
                         client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    (res,) = asyncio.run(svc.post_everywhere(VALID))
    assert res.status == "success" and res.public_access is False


# ---------- real integrations against mocked HTTP ----------
def test_mastodon_integration():
    seen = {}

    def handler(request: httpx.Request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"url": "https://mastodon.example/@me/1"})

    s = Settings(_env_file=None, mastodon_instance_url="https://mastodon.example/", mastodon_access_token="tok")
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    pub = asyncio.run(MastodonPlatform(s).publish(VALID, client))
    assert pub.url == "https://mastodon.example/@me/1"
    assert seen["auth"] == "Bearer tok" and seen["body"]["visibility"] == "public"


def test_bluesky_integration_builds_link_facet():
    calls = []

    def handler(request: httpx.Request):
        calls.append(request.url.path)
        if request.url.path.endswith("createSession"):
            return httpx.Response(200, json={"accessJwt": "jwt", "did": "did:plc:abc", "handle": "me.bsky.social"})
        body = json.loads(request.content)
        facet = body["record"]["facets"][0]
        text = body["record"]["text"].encode()
        assert text[facet["index"]["byteStart"]:facet["index"]["byteEnd"]] == b"https://example.com"
        return httpx.Response(200, json={"uri": "at://did:plc:abc/app.bsky.feed.post/3kxyz"})

    s = Settings(_env_file=None, bluesky_handle="me.bsky.social", bluesky_app_password="pw")
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    pub = asyncio.run(BlueskyPlatform(s).publish("Héllo wörld " + "https://example.com", client))
    assert pub.url == "https://bsky.app/profile/me.bsky.social/post/3kxyz"
    assert len(calls) == 2


def test_http_error_becomes_platform_error():
    s = Settings(_env_file=None, mastodon_instance_url="https://m.example", mastodon_access_token="bad")
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(401, text="invalid token")))
    with pytest.raises(PlatformError, match="HTTP 401"):
        asyncio.run(MastodonPlatform(s).publish(VALID, client))
