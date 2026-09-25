# -*- coding: utf-8 -*-
# notifica - Reusable API authentication mixin for Odoo controllers
#
# Usage:
#   class MyController(ApiAuthMixin, http.Controller):
#       def my_endpoint(self, **kwargs):
#           auth_error = self._verify_api_token()
#           if auth_error:
#               return auth_error

import logging

from odoo.http import request

from .response_mixin import ApiResponseMixin

_logger = logging.getLogger(__name__)


class ApiAuthMixin(ApiResponseMixin):
    """Verify API requests against a token stored in ir.config_parameter.

    Expects the token to be set at ``<prefix>.api_token`` in System Parameters.
    Inherits ``ApiResponseMixin`` to return structured error dicts via Pydantic.
    """

    _api_auth_prefix = 'comm_log'

    def _verify_api_token(self) -> dict | None:
        """Validate the API token from the ``X-API-Key`` header.

        Returns ``None`` when valid, or an error dict (serialised via
        ``ApiErrorResponse`` / ``_error_model``) ready to be returned
        by the controller endpoint.
        """
        expected_token = (
            request.env['ir.config_parameter']
            .sudo()
            .get_param(f'{self._api_auth_prefix}.api_token')
        )
        if not expected_token:
            _logger.warning(
                "%s.api_token not configured — rejecting all requests",
                self._api_auth_prefix,
            )
            return self._error('API token not configured on server')

        api_key = request.httprequest.headers.get('X-API-Key')
        if not api_key or api_key != expected_token:
            return self._error('Unauthorized')

        return None
