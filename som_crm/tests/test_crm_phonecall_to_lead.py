# -*- coding: utf-8 -*-
from odoo.tests.common import tagged, TransactionCase
from odoo.exceptions import ValidationError

try:
    import phonenumbers
except ImportError:
    phonenumbers = None


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
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })

        cls.other_user = cls.env['res.users'].create({
            'name': 'Other User',
            'login': 'other_user',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })

        cls.crm_category = cls.env['product.category'].create({
            'name': 'Test Category for Conversion'
        })

        cls.env.company.som_crm_call_category_id = cls.crm_category

        cls.other_category = cls.env['product.category'].create({
            'name': 'Other Category'
        })

        # --- Phone number for tests ---
        cls.test_phone_number = "+34666777888"
        cls.test_phone_number_unformatted = "666 777 888"

    def test_prepare_opportunity_vals(self):
        vals = self.phonecall._prepare_opportunity_vals()
        self.assertEqual(vals['contact_name'], 'John Doe')
        self.assertEqual(vals['email_from'], 'john@example.com')
        self.assertEqual(vals['phone'], '+34123456789')
        self.assertEqual(vals['vat'], 'ES12345678')

    def test_prepare_opportunity_vals_with_channel(self):
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
        self.assertEqual(vals['som_channel'], utm_medium_phone_id.id)

    def test_prepare_opportunity_vals_autoassigned(self):
        self.test_user.write({'som_call_center_user': 'operator test'})
        vals = self.phonecall._prepare_opportunity_vals()
        self.assertEqual(vals['user_id'], self.test_user.id)

    def test_prepare_opportunity_vals_no_operator(self):
        self.test_user.write({'som_call_center_user': 'operator test 2'})
        vals = self.phonecall._prepare_opportunity_vals()
        self.assertFalse(vals.get('user_id'))


    def mock_phonenumbers_parse(self, number, region):
        """
        Mock for the phonenumbers.parse method to avoid dependency on the external library.
        """
        # Simulates a basic phonenumber object structure
        class MockPhoneNumber:
            country_code = 34
            national_number = 666777888

        if number in (self.test_phone_number, self.test_phone_number_unformatted):
            return MockPhoneNumber()
        raise Exception("Unexpected phone number in mock.")

    def test_convert_to_new_opportunity(self):
        """
        Test the conversion of a phonecall to a NEW opportunity.
        """
        self.test_user.write({'som_call_center_user': 'operator test'})
        # Create the phonecall
        phonecall = self.env['crm.phonecall'].with_user(self.test_user).create({
            'name': 'Test call for new opportunity',
            'som_phone': self.test_phone_number,
            'som_operator': self.test_user.som_call_center_user,
        })

        # Execute the action
        result = phonecall.action_button_convert2opportunity()

        # --- Asserts ---
        self.assertTrue(
            phonecall.opportunity_id, "The phonecall should be linked to an opportunity.")
        self.assertEqual(phonecall.opportunity_id.phone_sanitized, self.test_phone_number,
                         "The sanitized phone in the opportunity must be correct.")
        self.assertIn(self.crm_category, phonecall.som_category_ids,
                      "The crm tag should have been added to the phonecall.")

        # Check that the result is a redirect action
        self.assertEqual(
            result.get('type'), 'ir.actions.act_window', "It should return a window action.")
        self.assertEqual(
            result.get('res_model'), 'crm.lead', "The action should point to the crm.lead model.")


    def test_assign_to_existing_opportunity(self):
        """
        Test that the call is assigned to an EXISTING opportunity if there is a match.
        """
        self.test_user.write({'som_call_center_user': 'operator test'})
        # First, create an opportunity with the phone number
        existing_opp = self.env['crm.lead'].create({
            'name': 'Existing Opportunity',
            'type': 'opportunity',
            'phone': self.test_phone_number_unformatted,
            'phone_sanitized': self.test_phone_number
        })
        opp_count_before = self.env['crm.lead'].search_count([])

        # Create the phonecall
        phonecall = self.env['crm.phonecall'].with_user(self.test_user).create({
            'name': 'Call for existing opportunity',
            'som_phone': self.test_phone_number_unformatted,
            'som_operator': self.test_user.som_call_center_user,
        })

        # Execute the action
        phonecall.action_button_convert2opportunity()

        opp_count_after = self.env['crm.lead'].search_count([])

        # --- Asserts ---
        self.assertEqual(
            opp_count_before, opp_count_after, "A new opportunity should not have been created.")
        self.assertEqual(
            phonecall.opportunity_id, existing_opp,
            "The phonecall must be linked to the existing opportunity.")


    def test_validation_error_no_phone(self):
        """
        Test that a ValidationError is raised if the call has no phone number.
        """
        phonecall = self.env['crm.phonecall'].with_user(self.test_user).create({
            'name': 'Call without phone',
            'som_phone': False,
        })

        # The function that fails is the internal 'do_', since the main one would open the wizard
        with self.assertRaises(ValidationError, msg="An exception should be raised if there is no phone number."):
            phonecall.do_action_button_convert2opportunity()

    def test_action_opens_wizard_for_different_user(self):
        """
        Test that the action to open a wizard is returned if the user is not the operator.
        """
        self.test_user.write({'som_call_center_user': 'operator test'})
        phonecall = self.env['crm.phonecall'].create({
            'name': 'Call with another operator',
            'som_operator': self.test_user.som_call_center_user,
            'som_phone': self.test_phone_number,
        })

        # Execute the action with a different user
        action = phonecall.with_user(self.other_user).action_button_convert2opportunity()

        # --- Asserts ---
        self.assertIsInstance(
            action, dict, "The result must be an action dictionary.")
        self.assertEqual(
            action.get('type'), 'ir.actions.act_window')
        self.assertEqual(
            action.get('res_model'), 'convert.call.wizard', "It should open the conversion wizard.")
        self.assertEqual(
            action.get('target'), 'new', "The wizard should open in a new window (modal).")
        self.assertIn(
            'default_phonecall_id', action.get('context'), "The context must contain the phonecall ID.")
        self.assertEqual(
            action['context']['default_phonecall_id'], phonecall.id)
