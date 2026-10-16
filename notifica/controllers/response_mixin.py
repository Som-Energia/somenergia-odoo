# -*- coding: utf-8 -*-
# notifica - Reusable API response mixin for Odoo controllers
#
# Provides generic ``_error()`` and ``_success()`` builders that
# serialize through Pydantic models. Controllers can override
# ``_error_model`` and ``_success_model`` to use extended schemas.

from ..schemas import ApiErrorResponse


class ApiResponseMixin:
    """Mixin that provides structured API response builders.

    Override ``_error_model`` and ``_success_model`` in subclasses
    to use extended Pydantic schemas for controller-specific fields.
    """

    _error_model = ApiErrorResponse

    def _error(self, message: str, errors: dict | None = None) -> dict:
        """Build an error response dict via Pydantic serialization."""
        return self._error_model(
            status='error', message=message, errors=errors,
        ).model_dump(exclude_none=True)
