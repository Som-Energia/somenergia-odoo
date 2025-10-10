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

    def test_create_lead_success(self):
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

    def test_create_lead_with_file(self):
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
