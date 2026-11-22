"""Pydantic request / response models."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils import find_links, link_error


class PostingRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "message": "Check out our latest business platform and grow your online visibility. https://example.com"
            }
        },
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Message to publish (max 200 chars) containing exactly one valid http(s) CTA link.",
    )

    @field_validator("message")
    @classmethod
    def validate_single_valid_link(cls, value: str) -> str:
        links = find_links(value)
        if not links:
            raise ValueError("Message must contain exactly one CTA link, but none was found.")
        if len(links) > 1:
            raise ValueError(f"Message must contain exactly one CTA link, but {len(links)} were found.")
        problem = link_error(links[0])
        if problem:
            raise ValueError(problem)
        return value


class PlatformResult(BaseModel):
    platform: str
    status: Literal["success", "failed"]
    posted_url: str | None = None
    public_access: bool = False
    date: str | None = None
    time: str | None = None
    error: str | None = None


class PostingResponse(BaseModel):
    success: bool = Field(description="True when at least one platform accepted the post.")
    results: list[PlatformResult]


class FieldError(BaseModel):
    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    success: bool = False
    errors: list[FieldError]
