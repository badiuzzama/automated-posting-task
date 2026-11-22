"""FastAPI entrypoint.  Run with:  uvicorn app.main:app --host 0.0.0.0 --port 4000"""
import logging
from functools import lru_cache

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.platforms import build_platforms
from app.schemas import PostingRequest, PostingResponse, ValidationErrorResponse
from app.services.posting_service import PostingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Automated Multi-Platform Posting System",
    version="1.0.0",
    description="Publishes one short message with a CTA link to several third-party platforms via their APIs.",
)


@lru_cache
def get_posting_service() -> PostingService:
    settings = get_settings()
    return PostingService(build_platforms(settings), timeout=settings.platform_timeout_seconds)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(p) for p in err["loc"] if p != "body") or "body",
            "message": err["msg"].removeprefix("Value error, "),
        }
        for err in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"success": False, "errors": errors})


@app.post(
    "/posting",
    response_model=PostingResponse,
    responses={422: {"model": ValidationErrorResponse, "description": "Invalid message"}},
    summary="Publish a message to all configured platforms",
)
async def posting(
    payload: PostingRequest, service: PostingService = Depends(get_posting_service)
) -> PostingResponse:
    results = await service.post_everywhere(payload.message)
    return PostingResponse(success=any(r.status == "success" for r in results), results=results)
