
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

## API

`POST http://localhost:4000/posting`

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