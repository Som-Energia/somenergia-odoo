# -*- coding: utf-8 -*-
# notifica - Pydantic schemas for API request/response validation

from pydantic import BaseModel, Field, field_validator

from .config import SUPPORTED_LANG_KEYS, ORIGIN_APP_DEFAULT


class CommLogCreateRequest(BaseModel):
    """Validate incoming API request body."""
    email: str = Field(..., description="Recipient email address")
    subject: str = Field(default="External Communication")
    body_html: str = Field(default="")
    origin_app: str = Field(default=ORIGIN_APP_DEFAULT)
    external_msg_id: str = Field(default="")
    lang: str = Field(default="es_ES", description="ISO locale code")

    @field_validator('lang')
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in SUPPORTED_LANG_KEYS:
            raise ValueError(
                f"Unsupported language '{v}'. "
                f"Must be one of: {', '.join(sorted(SUPPORTED_LANG_KEYS))}"
            )
        return v


class ApiErrorResponse(BaseModel):
    """Generic API error response. Extend for controller-specific fields."""
    status: str
    message: str | None = None
    errors: dict | None = None


class CommLogCreateResponse(ApiErrorResponse):
    """Structure API response payload."""
    message_id: int | None = None
    comm_log_id: int | None = None
