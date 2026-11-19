# -*- coding: utf-8 -*-
import json
import logging

from psycopg2 import IntegrityError, OperationalError

from odoo import SUPERUSER_ID, api, http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from ..models.crm_lead_integration import LeadIntakeError


_logger = logging.getLogger(__name__)
MAX_BODY_SIZE = 64 * 1024


class CRMPartnerLeadAPIController(http.Controller):

    @staticmethod
    def _response(data, status=200):
        return request.make_json_response(data, status=status)

    @http.route('/api/crm/partner/lead', type='http', auth='none',
                methods=['POST'], csrf=False, save_session=False)
    def create_partner_lead(self, **kwargs):
        try:
            # Use the server user's default company and a fresh context, never
            # session/default_* values inherited from a browser request.
            env = api.Environment(request.env.cr, SUPERUSER_ID, {})
            integration = env['som.crm.lead.integration']._authenticate_token(
                request.httprequest.headers.get('X-API-Key'))
            if not integration:
                raise LeadIntakeError('unauthorized', 'Provide a valid X-API-Key.', 401)
            integration._check_intake_enabled()
            if request.httprequest.mimetype != 'application/json':
                raise LeadIntakeError('unsupported_media_type', 'Use application/json.', 415)
            if request.httprequest.content_length is None:
                raise LeadIntakeError('length_required', 'Provide Content-Length.', 411)
            if request.httprequest.content_length > MAX_BODY_SIZE:
                raise LeadIntakeError('payload_too_large', 'Maximum body size is 64 KiB.', 413)
            # Werkzeug caches these bounded bytes so Odoo can replay the handler
            # after a database serialization failure without consuming an empty stream.
            body = request.httprequest.get_data(cache=True)
            if len(body) > MAX_BODY_SIZE:
                raise LeadIntakeError('payload_too_large', 'Maximum body size is 64 KiB.', 413)
            try:
                payload = json.loads(body.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                raise LeadIntakeError('invalid_json', 'Provide a valid UTF-8 JSON object.')
            # Catch errors OUTSIDE the savepoint so partial records cannot commit.
            with request.env.cr.savepoint():
                lead, created = integration._receive_lead(payload)
                result = {
                    'success': True, 'created': created, 'lead_id': lead.id,
                    'id_external_lead': lead.id_external_lead,
                }
            return self._response(result, 201 if created else 200)
        except LeadIntakeError as exc:
            return self._response({
                'success': False, 'error': exc.code, 'message': str(exc),
            }, exc.status)
        except (IntegrityError, OperationalError):
            # Preserve Odoo transaction retries (40001, deadlocks), including the
            # fresh-snapshot retry requested by concurrent identical submissions.
            raise
        except (AccessError, ValidationError):
            return self._response({
                'success': False, 'error': 'configuration_error',
                'message': 'The integration configuration could not process this lead.',
            }, 422)
        except Exception:
            # No payloads, credentials, personal data or raw exception messages.
            _logger.error('Unexpected error in collaborator lead intake')
            return self._response({
                'success': False, 'error': 'internal_error',
                'message': 'The lead could not be processed.',
            }, 500)
