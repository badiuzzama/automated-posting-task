# Automated Multi-Platform Posting System

A FastAPI service that publishes one short message (with a single CTA link) to
**six third-party platforms** through their official REST APIs, concurrently and
with per-platform failure isolation.

| # | Platform | API used | Posted URL | Docs |
|---|----------|----------|-----------|------|
| 1 | Mastodon | `POST /api/v1/statuses` | status URL | https://docs.joinmastodon.org/methods/statuses/ |
| 2 | Bluesky | AT Protocol `createSession` + `createRecord` (link facet included) | `bsky.app/profile/<handle>/post/<rkey>` | https://docs.bsky.app/docs/api/ |
| 3 | Telegram | Bot API `sendMessage` to a public channel | `t.me/<channel>/<id>` | https://core.telegram.org/bots/api#sendmessage |
| 4 | DEV Community | Forem `POST /api/articles` | article URL | https://developers.forem.com/api/v1 |
| 5 | GitHub Gist | `POST /gists` (public gist) | gist URL | https://docs.github.com/en/rest/gists/gists |
| 6 | Discord | Webhook execute (`?wait=true`) | message link (members only) | https://discord.com/developers/docs/resources/webhook |

> Platform selection is internal: the client only sends `message`.
> Platforms whose credentials are not configured are reported as `failed`
> ("Missing credentials: ...") while the rest still post.

## Project structure

```
automated-posting/
├── app/
│   ├── main.py                 # FastAPI app, POST /posting, 422 error handler
│   ├── schemas.py              # Pydantic request/response models + validation
│   ├── config.py               # Env-based settings (pydantic-settings)
│   ├── utils.py                # Link detection / URL validation
│   ├── platforms/
│   │   ├── base.py             # Platform ABC, PlatformError, Published
│   │   ├── mastodon.py  bluesky.py  telegram.py
│   │   └── devto.py  github_gist.py  discord.py
│   └── services/posting_service.py   # concurrent fan-out + error isolation
├── tests/test_posting.py
├── .env.example  requirements.txt  pytest.ini  README.md
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then fill in credentials
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Swagger UI: http://localhost:4000/docs

### Getting credentials (all have free tiers)

- **Mastodon** – Preferences → Development → New application (scope `write:statuses`) → copy access token. Set `MASTODON_INSTANCE_URL`.
- **Bluesky** – Settings → App Passwords → create one. Set `BLUESKY_HANDLE` and `BLUESKY_APP_PASSWORD`.
- **Telegram** – Talk to `@BotFather` → `/newbot`. Create a **public** channel, add the bot as admin, set `TELEGRAM_CHAT_ID=@yourchannel`.
- **DEV Community** – Settings → Extensions → *Generate API key* → `DEVTO_API_KEY`.
- **GitHub Gist** – Create a token with the `gist` scope → `GITHUB_TOKEN`.
- **Discord** – Channel settings → Integrations → Webhooks → Copy Webhook URL → `DISCORD_WEBHOOK_URL`.

`.env` is git-ignored. Never commit real credentials.

## API

`POST http://localhost:4000/posting`

### Validation rules
- 1–200 characters (after trimming whitespace)
- exactly **one** link, which must be a valid `http://` / `https://` URL with a real domain
- anything else → `422` with a clear message

### Sample request
```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform and grow your online visibility. https://example.com"}'
```

### Sample response (`200`)
`success` is `true` when at least one platform accepted the post. `public_access`
is verified with an anonymous GET of the posted URL (or `false` by design for
members-only links such as Discord).
```json
{
  "success": true,
  "results": [
    {"platform": "Mastodon", "status": "success", "posted_url": "https://mastodon.social/@you/115000000000000000",
     "public_access": true, "date": "2026-11-22", "time": "10:30:00", "error": null},
    {"platform": "Bluesky", "status": "success", "posted_url": "https://bsky.app/profile/you.bsky.social/post/3kabc123",
     "public_access": true, "date": "2026-11-22", "time": "10:30:01", "error": null},
    {"platform": "Telegram", "status": "failed", "posted_url": null, "public_access": false,
     "date": null, "time": null, "error": "Missing credentials: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"},
    {"platform": "DEV Community", "status": "failed", "posted_url": null, "public_access": false,
     "date": null, "time": null, "error": "DEV post failed: HTTP 401 {\"error\":\"unauthorized\"}"}
  ]
}
```
*(illustrative – your real output depends on the credentials you configure)*

### Sample validation errors (`422`)
```json
{"success": false, "errors": [{"field": "message", "message": "Message must contain exactly one CTA link, but 2 were found."}]}
```
```json
{"success": false, "errors": [{"field": "message", "message": "String should have at most 200 characters"}]}
```
```json
{"success": false, "errors": [{"field": "message", "message": "The CTA link has an invalid domain name."}]}
```

## Design notes
- **Isolation:** every platform runs in its own `asyncio` task with a timeout; `PlatformError`, network errors, timeouts and unexpected exceptions are all converted into a `failed` result for that platform only.
- **Extensibility:** add a platform by subclassing `Platform` (`name`, `required_settings`, `publish`) and registering it in `app/platforms/__init__.py`.
- **Security:** credentials come only from environment variables; error messages contain the API's response snippet, never your secrets.
- **Testability:** HTTP is injected (`httpx.AsyncClient`), so tests use `httpx.MockTransport` – no network or real keys needed.

## Tests
```bash
pytest -q
```
Covers validation (length, 0/2 links, bad domain/scheme/port), response shape,
failure isolation (auth error, crash, missing credentials, timeout), the public-access
check, and request construction for Mastodon and Bluesky.

## Demonstration (logs / screenshots)
After configuring your keys, run the sample `curl` above and add your terminal output
and a screenshot of `/docs` plus the live posts to `docs/screenshots/` (and/or `logs/`).
