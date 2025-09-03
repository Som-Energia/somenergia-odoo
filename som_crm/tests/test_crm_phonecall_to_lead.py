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
            'som_operator': 'operator test',
        })

        cls.test_user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'testuser@example.com',
        })

        cls.crm_category = cls.env['product.category'].create({
            'name': 'Test Category for Conversion'
        })

        cls.env.company.som_crm_call_category_id = cls.crm_category

        cls.other_category = cls.env['product.category'].create({
            'name': 'Other Category'
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

    def test_prepare_opportunity_vals_autoassigned(self):
        self.test_user.write({'som_call_center_user': 'operator test'})
        vals = self.phonecall._prepare_opportunity_vals()
        self.assertEqual(vals['user_id'], self.test_user.id)

    def test_prepare_opportunity_vals_no_operator(self):
        self.test_user.write({'som_call_center_user': 'operator test 2'})
        vals = self.phonecall._prepare_opportunity_vals()
        self.assertFalse(vals.get('user_id'))

    # tests cron
    def test_convert_phonecalls_with_correct_category(self):
        phonecalls = self.env['crm.phonecall'].create([
            {
                'name': 'Test Call 1',
                'som_category_ids': [(6, 0, [self.crm_category.id])],
                'state': 'open',
            },
            {
                'name': 'Test Call 2',
                'som_category_ids': [(6, 0, [self.crm_category.id])],
                'state': 'open',
            }
        ])

        self.assertFalse(phonecalls[0].opportunity_id)
        self.assertFalse(phonecalls[1].opportunity_id)

        self.env['crm.phonecall']._convert_to_opportunity_by_category()

        self.assertTrue(phonecalls[0].opportunity_id)
        self.assertTrue(phonecalls[1].opportunity_id)

        self.assertNotEqual(phonecalls[0].opportunity_id.id,
                            phonecalls[1].opportunity_id.id)

    def test_no_conversion_for_wrong_category(self):
        phonecall = self.env['crm.phonecall'].create({
            'name': 'Test Call Wrong Category',
            'som_category_ids': [(6, 0, [self.other_category.id])],
            'state': 'open',
        })

        self.env['crm.phonecall']._convert_to_opportunity_by_category()
        self.assertFalse(phonecall.opportunity_id)

    def test_no_conversion_for_calls_with_existing_opportunity(self):
        opportunity = self.env['crm.lead'].create({
            'name': 'Existing Opportunity',

        })

        phonecall = self.env['crm.phonecall'].create({
            'name': 'Test Call With Opportunity',
            'som_category_ids': [(6, 0, [self.crm_category.id])],
            'opportunity_id': opportunity.id,
            'state': 'open',
        })

        self.env['crm.phonecall']._convert_to_opportunity_by_category()
        self.assertEqual(phonecall.opportunity_id.id, opportunity.id)

    def test_no_category_configured_in_company(self):
        self.env.company.som_crm_call_category_id = False

        phonecall = self.env['crm.phonecall'].create({
            'name': 'Test Call',
            'som_category_ids': [(6, 0, [self.crm_category.id])],
            'state': 'open',
        })
        self.env['crm.phonecall']._convert_to_opportunity_by_category()

        self.assertFalse(phonecall.opportunity_id)

    def test_multiple_categories_on_phonecall(self):
        phonecall = self.env['crm.phonecall'].create({
            'name': 'Test Call Multiple Categories',
            'som_category_ids': [(6, 0, [self.crm_category.id, self.other_category.id])],
            'state': 'open',
        })

        self.env['crm.phonecall']._convert_to_opportunity_by_category()
        self.assertTrue(phonecall.opportunity_id)
