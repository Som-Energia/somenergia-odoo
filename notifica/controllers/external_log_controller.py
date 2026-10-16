import json as json_lib
import werkzeug.wrappers

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
from pydantic import ValidationError as PydanticValidationError

from ..schemas import CommLogCreateRequest, CommLogCreateResponse
from . import auth_mixin


class ExternalLogController(auth_mixin.ApiAuthMixin, http.Controller):

    _error_model = CommLogCreateResponse

    # ── Main endpoint ──────────────────────────────────────────────────

    @http.route('/api/v1/comm/log', type='http', auth='none', methods=['POST'], cors='*', csrf=False)
    def log_external_email(self, **kwargs):
        try:
            return self._handle_request()
        except json_lib.JSONDecodeError as e:
            return self._json_response(self._error(f'Invalid JSON: {e}'), status=400)
        except ValidationError as e:
            return self._json_response(self._error(str(e)), status=400)
        except Exception as e:
            return self._json_response(self._error(f'Internal error: {e}'), status=500)

    def _handle_request(self):
        data = self._parse_request()

        auth_error = self._verify_api_token()
        if auth_error:
            return self._json_response(auth_error, status=401)

        cleaned, err_fields = self._validate_payload(data)
        if err_fields:
            return self._json_response(
                self._error('Validation failed', errors=err_fields), status=400
            )

        partner = self._resolve_partner(cleaned['email'])
        if not partner:
            return self._json_response(
                self._error('Target client email address not found inside Odoo'), status=404
            )

        body = self._build_styled_body(cleaned)
        mail_msg = self._create_mail_message(partner, cleaned, body)
        comm_log = self._create_comm_log(partner, cleaned, body)

        return self._json_response({
            'status': 'success',
            'message_id': mail_msg.id,
            'comm_log_id': comm_log.id,
        }, status=200)

    # ── JSON response helper ──────────────────────────────────────────

    @staticmethod
    def _json_response(data, status=200):
        """Build a JSON HTTP response via werkzeug."""
        return werkzeug.wrappers.Response(
            response=json_lib.dumps(data, ensure_ascii=False),
            status=status,
            headers=[('Content-Type', 'application/json; charset=utf-8')],
        )

    # ── Request parsing ────────────────────────────────────────────────

    def _parse_request(self) -> dict:
        if not request.httprequest.data:
            return {}
        return json_lib.loads(request.httprequest.data.decode('utf-8'))

    # ── Payload validation ─────────────────────────────────────────────

    def _validate_payload(self, data: dict) -> tuple:
        try:
            return CommLogCreateRequest(**data).model_dump(), None
        except PydanticValidationError as exc:
            field_errors = {
                ".".join(str(loc) for loc in err['loc']): err['msg']
                for err in exc.errors()
            }
            return None, field_errors

    # ── Partner resolution ─────────────────────────────────────────────

    def _resolve_partner(self, email: str):
        return request.env['res.partner'].sudo().search(
            [('email', '=', email)], limit=1
        )

    # ── Body formatting ────────────────────────────────────────────────

    def _build_styled_body(self, cleaned: dict) -> str:
        origin_app = cleaned['origin_app']
        external_ref = cleaned.get('external_msg_id', '') or 'N/A'

        badge = (
            '<div class="alert alert-secondary py-1 mb-2" role="alert"'
            ' style="font-size: 0.85rem; border-left: 4px solid #714B67;">'
            '<strong>Logged via %s</strong>'
            ' | External Ref ID: %s'
            '</div>'
        ) % (origin_app.upper(), external_ref)

        return badge + (cleaned.get('body_html') or '')

    # ── Record creation ────────────────────────────────────────────────

    def _create_mail_message(self, partner, cleaned: dict, body: str):
        return request.env['mail.message'].sudo().create({
            'subject': cleaned.get('subject', 'External Communication'),
            'body': body,
            'model': 'res.partner',
            'res_id': partner.id,
            'message_type': 'comment',
            'subtype_id': request.env.ref('mail.mt_comment').id,
            'is_external_log': True,
        })

    def _create_comm_log(self, partner, cleaned: dict, body: str):
        return request.env['comm.log'].sudo().create({
            'partner_id': partner.id,
            'subject': cleaned.get('subject', 'External Communication'),
            'body_html': body,
            'source_type': 'external',
            'origin_app': cleaned['origin_app'],
            'status': 'sent',
            'lang': cleaned.get('lang', 'es_ES'),
            'external_ref_id': cleaned.get('external_msg_id', ''),
            'recipient_email': cleaned['email'],
        })
