# -*- coding: utf-8 -*-

from odoo.tests.common import tagged, TransactionCase


@tagged('som_phonecall_to_lead')
class TestCrmPhonecallToLead(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.phonecall = cls.env['crm.phonecall'].create({
            'name': 'Test call',
            'som_caller_name': 'John Doe',
            'email_from': 'john@example.com',
            'som_phone': '+34123456789',
            'som_caller_vat': 'ES12345678',
        })

    def test_prepare_opportunity_vals(self):
        vals = self.phonecall._prepare_opportunity_vals()
        self.assertEqual(vals['contact_name'], 'John Doe')
        self.assertEqual(vals['email_from'], 'john@example.com')
        self.assertEqual(vals['phone'], '+34123456789')
        self.assertEqual(vals['vat'], 'ES12345678')

    def test_prepare_opportunity_vals_with_medium(self):
        utm_medium_phone_id = self.env.ref('utm.utm_medium_phone', raise_if_not_found=False)
        if not utm_medium_phone_id:
            utm_medium_phone_id = self.env['utm.medium'].create({
                'name': 'Phone',
                'active': True
            })
            self.env['ir.model.data'].create({
                'module': 'utm',
                'name': 'utm_medium_phone',
                'model': 'utm.medium',
                'res_id': utm_medium_phone_id.id,
            })
        vals = self.phonecall._prepare_opportunity_vals()
        self.assertEqual(vals['medium_id'], utm_medium_phone_id.id)

    def test_prepare_opportunity_vals_without_medium(self):
        utm_medium_phone_id = self.env.ref('utm.utm_medium_phone', raise_if_not_found=False)
        if utm_medium_phone_id:
            utm_medium_phone_id.unlink()

        vals = self.phonecall._prepare_opportunity_vals()
        self.assertFalse(vals.get('medium_id'))
