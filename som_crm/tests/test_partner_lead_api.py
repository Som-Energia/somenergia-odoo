# -*- coding: utf-8 -*-
import hashlib
import json
from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import HttpCase, TransactionCase, tagged

from ..models.crm_lead_integration import LeadIntakeError
from ..pydantic.lead_models import CollaboratorLeadPayload


class CollaboratorIntakeFixture:

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('som_crm.collaborator_intake_enabled', True)
        cls.company = cls.env.company
        cls.company.write({
            'som_ff_auto_upcomming_activity': True,
            'som_ff_send_lead_confirmation_email': True,
            'som_ff_send_lead_confirmation_email_from': 'crm@example.com',
        })
        cls.salesperson = cls.env['res.users'].create({
            'name': 'Collaborator salesperson', 'login': 'collaborator_salesperson',
            'email': 'salesperson@example.com',
            'company_id': cls.company.id, 'company_ids': [(6, 0, cls.company.ids)],
            'groups_id': [(6, 0, [cls.env.ref('sales_team.group_sale_salesman_all_leads').id])],
        })
        cls.salesperson.action_create_employee()
        cls.team = cls.env['crm.team'].create({
            'name': 'Collaborator sales team', 'company_id': cls.company.id,
            'user_id': cls.salesperson.id,
            'crm_team_member_ids': [(0, 0, {'user_id': cls.salesperson.id})],
        })
        cls.integration = cls.env['som.crm.lead.integration'].create({
            'name': 'Collaborator A', 'code': 'test_collaborator_a',
            'team_id': cls.team.id,
            'stage_id': cls.env.ref('crm.stage_lead1').id,
            'enabled': True, 'salesperson_ids': [(6, 0, cls.salesperson.ids)],
        })
        cls.token = cls.integration.action_generate_api_key()['params']['message']

    def _payload(self, **changes):
        data = {
            'id_external_lead': '0000123', 'contact_name': 'CONTACTE exemple',
            'email': 'CONTACTE@example.com', 'phone': '+34 000 000 001',
            'cups': 'es0021000000000001ab', 'comments': 'Comentari\n<script>no</script>',
        }
        data.update(changes)
        return data

    def _receive(self, **changes):
        with self.env.cr.savepoint():
            return self.integration._receive_lead(self._payload(**changes))


@tagged('som_crm_partner_intake')
class TestCollaboratorIntake(CollaboratorIntakeFixture, TransactionCase):

    def test_pydantic_output_preserves_original_normalized_fingerprint(self):
        expected = {
            'id_external_lead': '0000123', 'contact_name': 'Contacte Exemple',
            'email': 'contacte@example.com', 'phone': '+34000000001',
            'lang': '', 'cups': 'ES0021000000000001AB',
            'comments': 'Comentari\n<script>no</script>',
        }
        raw = self._payload(
            id_external_lead=' 0000123 ', contact_name=' CONTACTE exemple ',
            email=' CONTACTE@EXAMPLE.COM ', cups=' es 0021 0000 0000 0001 ab ',
        )
        self.assertEqual(CollaboratorLeadPayload.model_validate(raw).model_dump(), expected)
        self.assertEqual(self.integration._validate_payload(raw), expected)
        original_fingerprint = hashlib.sha256(json.dumps(
            expected, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
        ).encode('utf-8')).hexdigest()
        with self.env.cr.savepoint():
            lead, _ = self.integration._receive_lead(raw)
        self.assertEqual(lead.som_intake_fingerprint, original_fingerprint)
        repeated, created = self._receive()
        self.assertFalse(created)
        self.assertEqual(repeated, lead)

    def test_optional_omissions_and_empty_values_are_equivalent(self):
        minimal = {
            'id_external_lead': 'minimal', 'contact_name': 'Contacte Exemple',
            'phone': '000000001',
        }
        explicit_empty = dict(minimal, email='', lang='', cups='', comments='')
        normalized = self.integration._validate_payload(minimal)
        self.assertEqual(normalized, self.integration._validate_payload(explicit_empty))
        self.assertEqual(normalized, {
            'id_external_lead': 'minimal', 'contact_name': 'Contacte Exemple',
            'email': '', 'phone': '000000001', 'lang': '', 'cups': '', 'comments': '',
        })
        self.assertEqual(normalized, self.integration._validate_payload(dict(
            minimal, id_external_lead='\x1cminimal\x1f',
        )))
        with self.env.cr.savepoint():
            first, created = self.integration._receive_lead(minimal)
            repeated, repeated_created = self.integration._receive_lead(explicit_empty)
        self.assertTrue(created)
        self.assertFalse(repeated_created)
        self.assertEqual(first, repeated)

    def test_pydantic_validation_preserves_public_error_codes(self):
        cases = [
            ([], 'invalid_data'),
            ({}, 'missing_fields'),
            ({'private-input@example.com': 'private-value'}, 'unknown_fields'),
            (self._payload(id_external_lead=' '), 'missing_fields'),
            (self._payload(contact_name=' '), 'missing_fields'),
            (self._payload(phone=True), 'invalid_data'),
            (self._payload(phone=123), 'invalid_data'),
            (self._payload(phone=['private-value']), 'invalid_data'),
            (self._payload(cups=None), 'invalid_data'),
            (self._payload(comments='private-value\x00'), 'invalid_data'),
            (self._payload(id_external_lead='a' * 129), 'invalid_data'),
            (self._payload(contact_name='a' * 256), 'invalid_data'),
            (self._payload(email='a' * 255), 'invalid_data'),
            (self._payload(phone='1' * 65), 'invalid_data'),
            (self._payload(comments='a' * 10001), 'invalid_data'),
            (self._payload(email='', phone=' '), 'missing_fields'),
            (self._payload(lang='fr_FR'), 'invalid_language'),
            (self._payload(cups='private-value'), 'invalid_cups'),
            (self._payload(email='private-value'), 'invalid_email'),
        ]
        for payload, code in cases:
            with self.subTest(code=code, payload=payload):
                with self.assertRaises(LeadIntakeError) as error:
                    self.integration._validate_payload(payload)
                self.assertEqual(error.exception.code, code)
                self.assertEqual(error.exception.status, 400)
                self.assertNotIn('private-value', str(error.exception))
                self.assertNotIn('private-input@example.com', str(error.exception))

    def test_create_maps_origin_cups_and_exactly_one_activity(self):
        lead, created = self._receive()
        self.assertTrue(created)
        self.assertEqual(lead.id_external_lead, '0000123')
        self.assertEqual(lead.som_lead_integration_id, self.integration)
        self.assertEqual(lead.som_channel, self.env.ref('som_crm.som_medium_collaborators'))
        self.assertEqual(lead.som_cups, 'ES0021000000000001AB')
        self.assertEqual(lead.user_id, self.salesperson)
        self.assertEqual(lead.team_id, self.team)
        self.assertEqual(lead.company_id, self.company)
        self.assertEqual(lead.contact_name, 'Contacte Exemple')
        self.assertEqual(lead.partner_id.email, 'contacte@example.com')
        self.assertEqual(len(lead.activity_ids), 1)
        self.assertEqual(lead.activity_ids.user_id, self.salesperson)
        self.assertTrue(any('&lt;script&gt;' in message.body for message in lead.message_ids))

    def test_original_request_payload_is_recorded_safely_in_chatter(self):
        payload = self._payload(
            id_external_lead='  audit-0001  ',
            contact_name=' CONTACTE audit ',
            comments='Nota original <script>alert("x")</script>\nSegona línia',
            cups='es 0021 0000 0000 0001 ab',
        )
        lead, created = self._receive(**payload)
        self.assertTrue(created)
        tracking = lead.message_ids.filtered(lambda message: '<pre>' in message.body)
        self.assertEqual(len(tracking), 1)
        body = tracking.body
        self.assertIn('Collaborator integration', body)
        self.assertIn('Collaborator A', body)
        self.assertIn('External lead ID', body)
        self.assertIn('audit-0001', body)
        # Preserve the received values, rather than only their normalized form.
        self.assertIn('"id_external_lead": "  audit-0001  "', body)
        self.assertIn('"contact_name": " CONTACTE audit "', body)
        self.assertIn('es 0021 0000 0000 0001 ab', body)
        self.assertIn('&lt;script&gt;', body)
        self.assertNotIn('<script>', body)
        self.assertNotIn(self.token, body)

    def test_retry_preserves_edited_archived_lead_without_side_effects(self):
        lead, _ = self._receive()
        lead.write({'active': False, 'contact_name': 'Edited by salesperson'})
        activities = lead.activity_ids
        repeated, created = self._receive(email='contacte@example.com', phone='+34000000001')
        self.assertFalse(created)
        self.assertEqual(repeated, lead)
        self.assertEqual(repeated.contact_name, 'Edited by salesperson')
        self.assertEqual(repeated.activity_ids, activities)

    def test_conflicting_retry_is_not_an_update(self):
        lead, _ = self._receive()
        with self.assertRaises(LeadIntakeError) as error:
            self._receive(phone='000000002')
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(lead.phone, '+34000000001')

    def test_same_external_id_allowed_for_another_integration(self):
        first, _ = self._receive()
        other = self.integration.copy({'name': 'Collaborator B', 'code': 'test_collaborator_b'})
        with self.env.cr.savepoint():
            second, created = other._receive_lead(self._payload())
        self.assertTrue(created)
        self.assertNotEqual(first, second)
        self.assertEqual(first.partner_id, second.partner_id)

    def test_empty_or_excluded_pool_has_no_fallback(self):
        self.integration.salesperson_ids = False
        lead, _ = self._receive()
        self.assertFalse(lead.user_id)
        self.assertFalse(lead.activity_ids)
        self.integration.salesperson_ids = self.salesperson
        self.salesperson.som_not_assign_opportunities = True
        other, _ = self._receive(id_external_lead='excluded-user')
        self.assertFalse(other.user_id)
        self.assertFalse(other.activity_ids)

    def test_activity_setting_is_respected_by_creation_and_cron(self):
        self.integration.create_initial_activity = False
        lead, _ = self._receive()
        self.assertEqual(lead.user_id, self.salesperson)
        self.assertFalse(lead.activity_ids)
        self.assertFalse(lead.create_upcomming_activity(force_today=True))
        self.env['crm.lead']._create_upcoming_activities()
        self.assertFalse(lead.activity_ids)

    def test_no_external_confirmation_or_welcome_even_from_actions(self):
        template = self.env.ref('som_crm.som_email_template_lead_confirmation')
        self.company.som_crm_lead_welcome_template_id = template
        self.company.som_crm_lead_welcome_stage_id = self.env.ref('crm.stage_lead2')
        lead, _ = self._receive()
        activities = lead.activity_ids
        with patch.object(type(template), 'send_mail') as send:
            self.assertFalse(lead.action_send_email_confirmation())
            self.assertFalse(lead.action_send_email_confirmation(invoice_received=True))
            lead.action_send_email_confirmation_multiple()
            lead._process_welcome()
        send.assert_not_called()
        with patch.object(type(lead), '_process_welcome', autospec=True) as welcome:
            self.env['crm.lead']._process_welcome_cron()
        if welcome.called:
            self.assertNotIn(lead.id, welcome.call_args[0][0].ids)
        self.assertEqual(lead.stage_id, self.integration.stage_id)
        self.assertEqual(lead.activity_ids, activities)

    def test_identity_is_immutable_and_not_copied(self):
        lead, _ = self._receive()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            lead.write({'som_lead_integration_id': False, 'id_external_lead': False})
        duplicate = lead.copy()
        self.assertFalse(duplicate.som_lead_integration_id)
        self.assertFalse(duplicate.id_external_lead)
        self.assertFalse(duplicate.som_intake_fingerprint)

    def test_normal_web_creation_does_not_require_external_id(self):
        lead = self.env['crm.lead'].create({'name': 'Manual or web opportunity', 'user_id': False})
        self.assertFalse(lead.id_external_lead)
        self.assertFalse(lead.som_lead_integration_id)

    def test_external_id_required_at_database_level(self):
        from psycopg2 import IntegrityError
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self.env['crm.lead'].create({
                'name': 'Missing external ID', 'som_lead_integration_id': self.integration.id,
            })

    def test_bad_payloads_are_rejected_before_creation(self):
        invalid_payloads = [
            [], {'files': []}, self._payload(id_external_lead=''),
            self._payload(contact_name=''), self._payload(phone=123),
            self._payload(email='', phone=''), self._payload(lang='fr_FR'),
            self._payload(cups='not-a-cups'), self._payload(email='invalid'),
            self._payload(user_id=self.salesperson.id),
        ]
        before = self.env['crm.lead'].search_count([])
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(LeadIntakeError):
                self.integration._receive_lead(payload)
        self.assertEqual(self.env['crm.lead'].search_count([]), before)

    def test_key_rotation_and_disabled_switches(self):
        integrations = self.env['som.crm.lead.integration']
        self.assertEqual(integrations._authenticate_token(self.token), self.integration)
        self.assertNotEqual(self.integration.api_key_digest, self.token)
        rotated = self.integration.action_generate_api_key()['params']['message']
        self.assertFalse(integrations._authenticate_token(self.token))
        self.assertEqual(integrations._authenticate_token(rotated), self.integration)
        self.integration.enabled = False
        with self.assertRaises(LeadIntakeError) as error:
            self._receive()
        self.assertEqual(error.exception.status, 403)
        self.integration.enabled = True
        self.env['ir.config_parameter'].sudo().set_param('som_crm.collaborator_intake_enabled', False)
        with self.assertRaises(LeadIntakeError) as error:
            self._receive()
        self.assertEqual(error.exception.status, 503)

    def test_salesperson_cannot_read_or_generate_credentials(self):
        integration = self.integration.with_user(self.salesperson)
        self.assertEqual(integration.name, 'Collaborator A')
        with self.assertRaises(AccessError):
            integration.read(['api_key_digest'])
        with self.assertRaises(AccessError):
            integration.action_generate_api_key()
        with self.assertRaises(AccessError):
            self.env['crm.lead'].with_user(self.salesperson).create({
                'name': 'Forged source', 'som_lead_integration_id': self.integration.id,
                'id_external_lead': 'forged',
            })
        with self.assertRaises(AccessError):
            self.env['crm.lead'].with_user(self.salesperson).with_context(
                default_som_lead_integration_id=self.integration.id,
                default_id_external_lead='forged-default',
            ).create({'name': 'Forged context source'})

    def test_global_switch_blocks_all_collaborators_and_defaults_to_disabled(self):
        other = self.integration.copy({'name': 'Collaborator B', 'code': 'test_global_switch_b'})
        params = self.env['ir.config_parameter'].sudo()
        for value in (False, 'False', '0', 'off'):
            params.set_param('som_crm.collaborator_intake_enabled', value)
            for integration in self.integration | other:
                with self.subTest(value=value, integration=integration.name):
                    with self.assertRaises(LeadIntakeError) as error:
                        integration._check_intake_enabled()
                    self.assertEqual(error.exception.status, 503)
        params.set_param('som_crm.collaborator_intake_enabled', True)
        self.integration._check_intake_enabled()
        other._check_intake_enabled()


@tagged('post_install', '-at_install', 'som_crm_partner_api')
class TestCollaboratorLeadHTTP(CollaboratorIntakeFixture, HttpCase):

    def _post(self, payload=None, token=None, body=None, content_type='application/json'):
        return self.url_open(
            '/api/crm/partner/lead',
            data=body if body is not None else json.dumps(payload if payload is not None else self._payload()),
            headers={'Content-Type': content_type, 'X-API-Key': token or self.token},
        )

    def test_http_creation_retry_conflict_and_origin(self):
        response = self._post()
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertTrue(result['created'])
        self.assertEqual(result['id_external_lead'], '0000123')
        retry = self._post()
        self.assertEqual(retry.status_code, 200, retry.text)
        self.assertEqual(retry.json()['lead_id'], result['lead_id'])
        self.assertFalse(retry.json()['created'])
        conflict = self._post(self._payload(comments='Changed data'))
        self.assertEqual(conflict.status_code, 409, conflict.text)

    def test_authentication_precedes_json_processing(self):
        response = self._post(body='invalid JSON', token='invalid-key')
        self.assertEqual(response.status_code, 401)
        response = self._post(body='invalid JSON')
        self.assertEqual(response.status_code, 400)

    def test_pydantic_errors_return_400_without_input_values(self):
        cases = [
            (self._payload(phone={'private-value': 'secret'}), 'invalid_data'),
            (self._payload(**{'private-input@example.com': 'secret'}), 'unknown_fields'),
        ]
        for payload, code in cases:
            with self.subTest(code=code):
                response = self._post(payload)
                self.assertEqual(response.status_code, 400, response.text)
                self.assertEqual(response.json()['error'], code)
                self.assertNotIn('private-value', response.text)
                self.assertNotIn('private-input@example.com', response.text)
                self.assertNotIn('secret', response.text)

    def test_disabled_channel_and_integration(self):
        self.integration.enabled = False
        self.assertEqual(self._post().status_code, 403)
        self.integration.enabled = True
        self.env['ir.config_parameter'].sudo().set_param('som_crm.collaborator_intake_enabled', False)
        self.assertEqual(self._post().status_code, 503)

    def test_invalid_shape_media_type_and_size(self):
        self.assertEqual(self._post(payload=[]).status_code, 400)
        self.assertEqual(self._post(content_type='text/plain').status_code, 415)
        self.assertEqual(self._post(body=' ' * (64 * 1024 + 1)).status_code, 413)

    def test_late_failure_rolls_back_opportunity_contact_and_activity(self):
        model = type(self.integration)
        original_receive = model._receive_lead
        before_leads = self.env['crm.lead'].search_count([])
        before_partners = self.env['res.partner'].search_count([])
        before_activities = self.env['mail.activity'].search_count([])

        def fail_after_creation(integration, payload):
            original_receive(integration, payload)
            raise ValidationError('Simulated late failure')

        with patch.object(model, '_receive_lead', fail_after_creation):
            response = self._post()
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.env['crm.lead'].search_count([]), before_leads)
        self.assertEqual(self.env['res.partner'].search_count([]), before_partners)
        self.assertEqual(self.env['mail.activity'].search_count([]), before_activities)
