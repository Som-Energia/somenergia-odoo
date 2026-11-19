# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import re
import secrets

from markupsafe import Markup, escape
from psycopg2 import errors
from pydantic import ValidationError as PydanticValidationError

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import email_normalize, str2bool

from .lead_intake import normalize_contact_data
from ..pydantic.lead_models import CollaboratorLeadPayload


class LeadIntakeError(Exception):
    """An expected, public API error, with no internal exception details."""

    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.status = status


class CRMLeadIntegration(models.Model):
    _name = 'som.crm.lead.integration'
    _description = 'Collaborator lead integration'
    _order = 'name, id'

    name = fields.Char(required=True)
    code = fields.Char(required=True, copy=False, index=True)
    partner_id = fields.Many2one('res.partner')
    active = fields.Boolean(default=True)
    enabled = fields.Boolean(default=False)
    team_id = fields.Many2one('crm.team', required=True)
    stage_id = fields.Many2one(
        'crm.stage', required=True, default=lambda self: self.env.ref('crm.stage_lead1'),
    )
    salesperson_ids = fields.Many2many(
        'res.users', string='Receiving salespeople',
        domain=[('share', '=', False), ('active', '=', True)],
    )
    create_initial_activity = fields.Boolean(default=True)
    api_key_selector = fields.Char(
        copy=False, index=True, groups='base.group_system', readonly=True,
    )
    api_key_digest = fields.Char(
        copy=False, groups='base.group_system', readonly=True,
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The integration code must be unique.'),
        ('key_selector_unique', 'unique(api_key_selector)', 'The API key must be unique.'),
    ]

    @api.constrains('code', 'name')
    def _check_identification(self):
        for integration in self:
            if not integration.name.strip() or not re.fullmatch(
                    r'[a-zA-Z0-9_-]{1,64}', integration.code):
                raise ValidationError(_(
                    'Provide a name and a code of up to 64 letters, digits, hyphens or underscores.'
                ))

    @api.constrains('stage_id', 'team_id', 'salesperson_ids')
    def _check_routing(self):
        self._check_stage_team_routing()
        for integration in self:
            for user in integration.salesperson_ids:
                if user.share or not user.has_group('sales_team.group_sale_salesman'):
                    raise ValidationError(_(
                        'Receiving salespeople must be internal CRM users.'
                    ))
                if user not in integration.team_id.member_ids and user != integration.team_id.user_id:
                    raise ValidationError(_('Receiving salespeople must belong to the selected team.'))

    def _check_stage_team_routing(self):
        """Recheck structural routing while allowing stale users to be filtered out."""
        for integration in self:
            if integration.stage_id.is_won or (
                    integration.stage_id.team_id and
                    integration.stage_id.team_id != integration.team_id):
                raise ValidationError(_('Select a non-won stage compatible with the sales team.'))

    def action_generate_api_key(self):
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_('Only administrators can generate integration credentials.'))
        self.check_access_rights('write')
        self.check_access_rule('write')
        selector = secrets.token_hex(16)
        token = 'somcrm.%s.%s' % (selector, secrets.token_urlsafe(32))
        self.write({
            'api_key_selector': selector,
            'api_key_digest': hashlib.sha256(token.encode('utf-8')).hexdigest(),
        })
        # The clear token is returned once, never stored in a field or chatter.
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Copy this API key now; the previous key is no longer valid'),
                'message': token,
                'sticky': True,
                'type': 'warning',
            },
        }

    @api.model
    def _authenticate_token(self, token):
        if not isinstance(token, str) or not re.fullmatch(
                r'somcrm\.[0-9a-f]{32}\.[A-Za-z0-9_-]{43}', token):
            return self.browse()
        integration = self.sudo().with_context(active_test=False).search([
            ('api_key_selector', '=', token.split('.')[1]),
        ], limit=1)
        digest = hashlib.sha256(token.encode('utf-8')).hexdigest()
        if not integration or not hmac.compare_digest(integration.api_key_digest or '', digest):
            return self.browse()
        return integration

    def _check_intake_enabled(self):
        self.ensure_one()
        if not self.active or not self.enabled:
            raise LeadIntakeError('integration_disabled', 'This integration is disabled.', 403)
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'som_crm.collaborator_intake_enabled', default='False',
        )
        if not str2bool(enabled, default=False):
            raise LeadIntakeError('channel_disabled', 'Collaborator intake is temporarily disabled.', 503)

    @api.model
    def _validate_payload(self, data):
        try:
            # Include all defaults: omitting optional fields and sending empty
            # strings must keep producing the original idempotency fingerprint.
            result = CollaboratorLeadPayload.model_validate(data).model_dump()
        except PydanticValidationError as exc:
            details = exc.errors(include_input=False, include_context=False, include_url=False)
            # Unknown input keys never appear in the public response. Prefer this
            # error even if Pydantic also reports missing required fields.
            if any(error['type'] == 'extra_forbidden' for error in details):
                raise LeadIntakeError('unknown_fields', 'The body contains unsupported fields.') from None
            error = details[0]
            kind = error['type']
            field = error['loc'][0] if error['loc'] else None
            if kind in ('model_type', 'dict_type'):
                raise LeadIntakeError('invalid_data', 'The JSON body must be an object.') from None
            if kind in ('missing', 'string_too_short'):
                raise LeadIntakeError(
                    'missing_fields', 'id_external_lead and contact_name are required.',
                ) from None
            if field in CollaboratorLeadPayload.model_fields:
                if kind == 'string_type':
                    raise LeadIntakeError('invalid_data', '%s must be a string.' % field) from None
                if kind == 'string_too_long':
                    raise LeadIntakeError('invalid_data', '%s is too long.' % field) from None
            if kind in ('invalid_data', 'missing_fields', 'invalid_language', 'invalid_cups'):
                # Only our custom validators produce these static, safe messages.
                raise LeadIntakeError(kind, error['msg']) from None
            raise LeadIntakeError('invalid_data', 'The payload contains invalid data.') from None
        if result['email'] and not email_normalize(result['email']):
            raise LeadIntakeError('invalid_email', 'Provide a valid email address.')
        return result

    def _select_salesperson(self):
        self.ensure_one()
        # Re-evaluate current eligibility, including users edited after setup.
        users = self.salesperson_ids.filtered(lambda user: (
            user.active and not user.share and
            user.has_group('sales_team.group_sale_salesman') and
            (user in self.team_id.member_ids or user == self.team_id.user_id)
        ))
        return self.team_id._get_random_assignable_member(users, approved_leaves_only=True)

    def _receive_lead(self, payload):
        """Private service: caller must authenticate and wrap the entire call in a savepoint."""
        self.ensure_one()
        self._check_intake_enabled()
        data = self._validate_payload(payload)
        lead_model = self.env['crm.lead']
        fingerprint = hashlib.sha256(json.dumps(
            data, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
        ).encode('utf-8')).hexdigest()
        existing = lead_model.with_context(active_test=False).search([
            ('som_lead_integration_id', '=', self.id),
            ('id_external_lead', '=', data['id_external_lead']),
        ], limit=1)
        if existing:
            if existing.som_intake_fingerprint != fingerprint:
                raise LeadIntakeError('external_id_conflict', 'This external ID has different data.', 409)
            return existing, False

        # Integration writes are validated strictly by _check_routing(). At
        # intake time, configured users may have since left the team or lost
        # eligibility; _select_salesperson filters them and can return no user.
        self._check_stage_team_routing()
        lang = self.env['res.lang']
        if data['lang']:
            lang = lang.search([('code', '=', data['lang'])], limit=1)
            if not lang:
                raise LeadIntakeError('invalid_language', 'The requested language is not active.')
        values = normalize_contact_data(data)
        values.update({
            'name': values['contact_name'], 'type': 'opportunity', 'user_id': False,
            'company_id': self.env.company.id, 'team_id': self.team_id.id,
            'stage_id': self.stage_id.id,
            'som_channel': self.env.ref('som_crm.som_medium_collaborators').id,
            'som_lead_integration_id': self.id,
            'id_external_lead': data['id_external_lead'],
            'som_intake_fingerprint': fingerprint,
            'som_cups': data['cups'] or False, 'lang_id': lang.id or False,
        })
        try:
            with self.env.cr.savepoint():
                lead = lead_model.create(values)
        except errors.UniqueViolation as exc:
            if exc.diag.constraint_name != 'crm_lead_som_external_lead_unique':
                raise
            # Odoo 16 uses REPEATABLE READ. A concurrent winner is not necessarily
            # visible in this snapshot. Ask its HTTP retry wrapper to restart the
            # entire transaction with a fresh snapshot, rather than search here.
            self.env.cr.execute("""
                DO $$ BEGIN
                    RAISE EXCEPTION 'Concurrent collaborator lead intake'
                    USING ERRCODE = '40001';
                END $$;
            """)

        user = self._select_salesperson()
        if user:
            lead.user_id = user
        lead.assign_partner()
        if self.create_initial_activity and user:
            lead.create_upcomming_activity(force_today=True)
        request_json = json.dumps(payload, ensure_ascii=False, indent=2)
        lead.message_post(
            body=Markup(
                '<p><strong>%s</strong>: %s<br/><strong>%s</strong>: %s</p><pre>%s</pre>'
            ) % (
                _('Collaborator integration'), self.name,
                _('External lead ID'), data['id_external_lead'],
                escape(request_json),
            ),
            message_type='comment', subtype_xmlid='mail.mt_note',
        )
        if data['comments']:
            lead.message_post(
                body=Markup('<p>%s</p>') % escape(data['comments']).replace('\n', Markup('<br/>')),
                message_type='comment', subtype_xmlid='mail.mt_note',
            )
        return lead, True
