# -*- coding: utf-8 -*-
import json
import base64
import markupsafe
from odoo.tests.common import TransactionCase, HttpCase, tagged
from odoo.exceptions import ValidationError
from odoo import http


@tagged('som_test_crm_lead_api_http')
class TestCRMLeadAPIHttp(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Test API key
        cls.env['ir.config_parameter'].sudo().set_param('som_crm.api_key', 'test_api_key_123')

        # Sales Team User
        cls.sales_user = cls.env['res.users'].create({
            'name': 'Sales User',
            'login': 'sales_user',
            'email': 'sales@test.com',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })

        # Stage_1
        cls.stage_lead1 = cls.env.ref(
            'crm.stage_lead1', raise_if_not_found=False
        ) or False
        if not cls.stage_lead1:
            cls.stage_lead1 = cls.env['crm.stage'].create({
                'name': 'Stage 1',
            })
            cls.env['ir.model.data'].create({
                'name': 'stage_lead1',
                'module': 'crm',
                'model': 'crm.stage',
                'res_id': cls.stage_lead1.id,
            })

        # Stage_2
        cls.stage_lead2 = cls.env.ref(
            'crm.stage_lead2', raise_if_not_found=False
        ) or False
        if not cls.stage_lead2:
            cls.stage_lead2 = cls.env['crm.stage'].create({
                'name': 'Stage 2',
            })
            cls.env['ir.model.data'].create({
                'name': 'stage_lead2',
                'module': 'crm',
                'model': 'crm.stage',
                'res_id': cls.stage_lead2.id,
            })

        # Sales Team
        cls.sales_team = cls.env.ref(
            'sales_team.team_sales_department', raise_if_not_found=False
        ) or False
        if not cls.sales_team:
            cls.sales_team = cls.env['crm.team'].create({
                'name': 'Sales Department',
            })
            cls.env['ir.model.data'].create({
                'name': 'team_sales_department',
                'module': 'sales_team',
                'model': 'crm.team',
                'res_id': cls.sales_team.id,
            })
        cls.sales_team.user_id = cls.sales_user

        # UTM Webform Medium
        cls.webform_medium = cls.env.ref(
            'som_crm.som_medium_webform', raise_if_not_found=False
        ) or False
        if not cls.webform_medium:
            cls.webform_medium = cls.env['utm.medium'].create({'name': 'Web Form'})
            cls.env['ir.model.data'].create({
                'name': 'som_medium_webform',
                'module': 'som_crm',
                'model': 'utm.medium',
                'res_id': cls.webform_medium.id,
            })

        # UTM Webform Simulation Medium
        cls.webform_simulation_medium = cls.env.ref(
            'som_crm.som_medium_webform_simulation', raise_if_not_found=False
        ) or False
        if not cls.webform_simulation_medium:
            cls.webform_simulation_medium = cls.env['utm.medium'].create(
                {'name': 'Web Form Simulation'}
            )
            cls.env['ir.model.data'].create({
                'name': 'som_medium_webform_simulation',
                'module': 'som_crm',
                'model': 'utm.medium',
                'res_id': cls.webform_simulation_medium.id,
            })

    def test_create_lead_success_without_file(self):
        data = {
            'contact_name': 'Test CONTACT ok',
            'email': 'TEST@EXAMPLE.COM',
            'phone': '+34123456789',
        }

        response = self.url_open(
            '/api/crm/lead',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key_123'
            }
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(response_data['success'])
        self.assertIn('lead_id', response_data)

        id_created_lead = response_data['lead_id']
        created_lead_id = self.env['crm.lead'].browse(id_created_lead)
        self.assertEqual(created_lead_id.contact_name, "Test Contact Ok")
        self.assertEqual(created_lead_id.email_from, "test@example.com")
        self.assertEqual(created_lead_id.stage_id, self.stage_lead1)
        self.assertEqual(created_lead_id.medium_id, self.webform_medium)
        self.assertEqual(created_lead_id.user_id, self.sales_user)

    def test_create_lead_success_with_file(self):
        fake_pdf = base64.b64encode(b'%PDF fake content').decode('utf-8')

        data = {
            'contact_name': 'TEST Contact with File',
            'email': 'TEST@EXAMPLE.COM',
            'files': [{
                'filename': 'test_document.pdf',
                'content': fake_pdf,
                'mimetype': 'application/pdf'
            }]
        }

        response = self.url_open(
            '/api/crm/lead',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key_123'
            }
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(response_data['success'])
        self.assertIn('attachments', response_data)
        self.assertEqual(len(response_data['attachments']), 1)

        id_created_lead = response_data['lead_id']
        created_lead_id = self.env['crm.lead'].browse(id_created_lead)
        self.assertEqual(created_lead_id.contact_name, "Test Contact With File")
        self.assertEqual(created_lead_id.email_from, "test@example.com")
        self.assertEqual(created_lead_id.stage_id, self.stage_lead2)
        self.assertEqual(created_lead_id.medium_id, self.webform_simulation_medium)
        self.assertEqual(created_lead_id.user_id, self.sales_user)

    def test_create_lead_unauthorized(self):
        data = {
            'contact_name': 'Test Contact',
            'email': 'test@example.com'
        }

        # Without X-API-Key
        response = self.url_open(
            '/api/crm/lead',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
            }
        )

        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error'], 'Authentication required')

        # Wrong X-API-Key
        response = self.url_open(
            '/api/crm/lead',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'wrong_key_123'
            }
        )

        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error'], 'Authentication required')

    def test_create_lead_invalid_json(self):
        response = self.url_open(
            '/api/crm/lead',
            data='{"invalid_json":}',
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key_123'
            }
        )
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['error'], 'Invalid JSON')

    def test_api_documentation(self):
        response = self.url_open('/api/crm/docs')

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertIn('api_info', response_data)
        self.assertIn('endpoints', response_data)
        self.assertIn('authentication', response_data)
        self.assertIn('testing', response_data)

    def test_create_lead_success_tracking_no_files(self):
        data = {
            'contact_name': 'Test Contact',
            'email': 'test@example.com',
            'phone': '+34123456789',
        }

        response = self.url_open(
            '/api/crm/lead',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key_123'
            }
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(response_data['success'])
        self.assertIn('lead_id', response_data)

        id_created_lead = response_data['lead_id']
        created_lead_id = self.env['crm.lead'].browse(id_created_lead)
        message = created_lead_id.message_ids.sorted('date', reverse=True)[0]
        expected_part = markupsafe.Markup('<pre>{\n  "contact_name": "Test Contact",\n  "email": "test@example.com",\n  "phone": "+34123456789",\n  "files_count": 0\n}</pre>')
        self.assertIn(
            expected_part, message.body,
            "The tracking message does not contain the expected JSON data."
        )

    def test_create_lead_success_tracking_with_files(self):
        fake_pdf = base64.b64encode(b'%PDF fake content').decode('utf-8')

        data = {
            'contact_name': 'Test Contact with File',
            'email': 'test@example.com',
            'files': [{
                'filename': 'test_document.pdf',
                'content': fake_pdf,
                'mimetype': 'application/pdf'
            }]
        }

        response = self.url_open(
            '/api/crm/lead',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'test_api_key_123'
            }
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(response_data['success'])
        self.assertIn('attachments', response_data)
        self.assertEqual(len(response_data['attachments']), 1)

        id_created_lead = response_data['lead_id']
        created_lead_id = self.env['crm.lead'].browse(id_created_lead)
        message = created_lead_id.message_ids.sorted('date', reverse=True)[0]
        expected_part = markupsafe.Markup('<pre>{\n  "contact_name": "Test Contact with File",\n  "email": "test@example.com",\n  "files_count": 1\n}</pre>')
        self.assertIn(
            expected_part, message.body,
            "The tracking message does not contain the expected JSON data."
        )
