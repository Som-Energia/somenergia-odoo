# -*- coding: utf-8 -*-
from datetime import date
from unittest.mock import patch
from odoo.tests.common import TransactionCase, tagged


@tagged('som_welcome_email')
class TestSendWelcomeEmail(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.origin_stage = cls.env.ref('crm.stage_lead1')
        cls.target_stage = cls.env['crm.stage'].create({'name': 'Welcome Sent'})

        cls.lang_ca = cls.env.ref('base.lang_ca_ES', raise_if_not_found=False)
        cls.lang_es = cls.env.ref('base.lang_es', raise_if_not_found=False)

        cls.partner_ca = cls.env['res.partner'].create({
            'name': 'Partner CA',
            'email': 'partner.ca@example.com',
            'lang': cls.lang_ca.code if cls.lang_ca else 'ca_ES',
        })
        cls.partner_es = cls.env['res.partner'].create({
            'name': 'Partner ES',
            'email': 'partner.es@example.com',
            'lang': cls.lang_es.code if cls.lang_es else 'es_ES',
        })
        cls.partner_no_email = cls.env['res.partner'].create({
            'name': 'Partner No Email',
        })

        cls.template_ca = cls.env['mail.template'].create({
            'name': 'Welcome CA',
            'model_id': cls.env['ir.model']._get('crm.lead').id,
            'subject': 'Benvinguda',
            'body_html': '<p>Hola</p>',
        })
        cls.template_es = cls.env['mail.template'].create({
            'name': 'Welcome ES',
            'model_id': cls.env['ir.model']._get('crm.lead').id,
            'subject': 'Bienvenida',
            'body_html': '<p>Hola</p>',
        })

        cls.env.company.som_crm_lead_welcome_template_id = cls.template_ca
        cls.env.company.som_crm_lead_welcome_template_es_id = cls.template_es
        cls.env.company.som_crm_lead_welcome_stage_id = cls.target_stage

    def _create_lead(self, partner, stage=None, lang=None):
        vals = {
            'name': f'Lead {partner.name}',
            'partner_id': partner.id,
            'email_from': partner.email,
            'stage_id': (stage or self.origin_stage).id,
        }
        if lang:
            vals['lang_id'] = lang.id
        return self.env['crm.lead'].create(vals)

    # --- _process_welcome ---

    def test_ca_partner_uses_ca_template(self):
        lead = self._create_lead(self.partner_ca)
        with patch.object(type(self.template_ca), 'send_mail') as mock_send:
            lead._process_welcome()
            mock_send.assert_called_once_with(lead.id, force_send=True)
        self.assertEqual(lead.stage_id, self.target_stage)

    def test_es_partner_uses_es_template(self):
        lead = self._create_lead(self.partner_es, lang=self.lang_es)
        with patch.object(type(self.template_es), 'send_mail') as mock_send:
            lead._process_welcome()
            mock_send.assert_called_once_with(lead.id, force_send=True)
        self.assertEqual(lead.stage_id, self.target_stage)

    def test_es_partner_falls_back_to_ca_if_no_es_template(self):
        self.env.company.som_crm_lead_welcome_template_es_id = False
        lead = self._create_lead(self.partner_es, lang=self.lang_es)
        with patch.object(type(self.template_ca), 'send_mail') as mock_send:
            lead._process_welcome()
            mock_send.assert_called_once_with(lead.id, force_send=True)
        self.assertEqual(lead.stage_id, self.target_stage)
        # restore
        self.env.company.som_crm_lead_welcome_template_es_id = self.template_es

    def test_falls_back_to_ca_when_lead_lang_is_empty(self):
        lead = self._create_lead(self.partner_es)
        with patch.object(type(self.template_ca), 'send_mail') as mock_send:
            lead._process_welcome()
            mock_send.assert_called_once_with(lead.id, force_send=True)
        self.assertEqual(lead.stage_id, self.target_stage)

    def test_skips_lead_without_partner(self):
        lead = self._create_lead(self.partner_ca)
        lead.partner_id = False
        with patch.object(type(self.template_ca), 'send_mail') as mock_send:
            lead._process_welcome()
            mock_send.assert_not_called()
        self.assertEqual(lead.stage_id, self.origin_stage)

    def test_skips_lead_without_email(self):
        lead = self._create_lead(self.partner_no_email)
        lead.email_from = False
        with patch.object(type(self.template_ca), 'send_mail') as mock_send:
            lead._process_welcome()
            mock_send.assert_not_called()
        self.assertEqual(lead.stage_id, self.origin_stage)

    def test_skips_lead_in_wrong_stage(self):
        lead = self._create_lead(self.partner_ca, stage=self.target_stage)
        with patch.object(type(self.template_ca), 'send_mail') as mock_send:
            lead._process_welcome()
            mock_send.assert_not_called()
        self.assertEqual(lead.stage_id, self.target_stage)

    def test_skips_all_if_no_template_ca(self):
        self.env.company.som_crm_lead_welcome_template_id = False
        lead = self._create_lead(self.partner_ca)
        with patch.object(type(self.template_ca), 'send_mail') as mock_send:
            lead._process_welcome()
            mock_send.assert_not_called()
        # restore
        self.env.company.som_crm_lead_welcome_template_id = self.template_ca

    def test_skips_all_if_no_target_stage(self):
        self.env.company.som_crm_lead_welcome_stage_id = False
        lead = self._create_lead(self.partner_ca)
        with patch.object(type(self.template_ca), 'send_mail') as mock_send:
            lead._process_welcome()
            mock_send.assert_not_called()
        # restore
        self.env.company.som_crm_lead_welcome_stage_id = self.target_stage

    def test_continues_after_error_on_one_lead(self):
        lead_ca = self._create_lead(self.partner_ca)
        lead_es = self._create_lead(self.partner_es)

        def mock_send(lead_id, force_send):
            if lead_id == lead_ca.id:
                raise Exception("SMTP error")

        with patch.object(type(self.template_ca), 'send_mail', side_effect=mock_send), \
             patch.object(type(self.template_es), 'send_mail', side_effect=mock_send):
            (lead_ca | lead_es)._process_welcome()

        self.assertEqual(lead_ca.stage_id, self.origin_stage)
        self.assertEqual(lead_es.stage_id, self.target_stage)
        self.assertEqual(lead_ca.stage_id, self.origin_stage)
        self.assertEqual(lead_es.stage_id, self.target_stage)

    # --- _process_welcome_cron ---

    def test_cron_finds_eligible_leads(self):
        lead = self._create_lead(self.partner_ca)
        with patch.object(type(self.template_ca), 'send_mail'):
            self.env['crm.lead']._process_welcome_cron()
        self.assertEqual(lead.stage_id, self.target_stage)

    # --- activitats obertes ---

    def _create_activity(self, lead):
        activity_type = self.env.ref(
            'mail.mail_activity_data_todo', raise_if_not_found=False
        ) or self.env['mail.activity.type'].search([], limit=1)
        return self.env['mail.activity'].create({
            'res_model_id': self.env['ir.model']._get('crm.lead').id,
            'res_id': lead.id,
            'activity_type_id': activity_type.id,
            'summary': 'Activitat de prova',
            'user_id': self.env.user.id,
            'date_deadline': date.today(),
        })

    def test_activities_marked_done_on_success(self):
        lead = self._create_lead(self.partner_ca)
        activity = self._create_activity(lead)
        self.assertTrue(activity.exists())

        with patch.object(type(self.template_ca), 'send_mail'):
            lead._process_welcome()

        self.assertFalse(activity.exists())
        self.assertEqual(lead.stage_id, self.target_stage)

    def test_no_activities_does_not_fail(self):
        lead = self._create_lead(self.partner_ca)
        lead.activity_ids.unlink()

        with patch.object(type(self.template_ca), 'send_mail'):
            lead._process_welcome()

        self.assertEqual(lead.stage_id, self.target_stage)

    def test_activities_not_marked_done_if_email_fails(self):
        lead = self._create_lead(self.partner_ca)
        activity = self._create_activity(lead)
        self.assertTrue(activity.exists())

        with patch.object(type(self.template_ca), 'send_mail', side_effect=Exception("SMTP error")):
            lead._process_welcome()

        self.assertTrue(activity.exists())
        self.assertEqual(lead.stage_id, self.origin_stage)
