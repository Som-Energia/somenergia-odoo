# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
from odoo.fields import Datetime, Date

@tagged('som_lead')
class TestCrmLead(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestCrmLead, cls).setUpClass()

        # --- Create necessary records for the tests ---
        cls.partner_by_email = cls.env['res.partner'].create({
            'name': 'Partner By Email',
            'email': 'test.email@example.com',
        })
        cls.partner_by_phone = cls.env['res.partner'].create({
            'name': 'Partner By Phone',
            'phone': '+1122334455',
        })
        cls.another_partner = cls.env['res.partner'].create({
            'name': 'Another Partner',
        })

        # UTM direct medium
        cls.direct_medium = cls.env.ref(
            'utm.utm_medium_direct', raise_if_not_found=False
        ) or False
        if not cls.direct_medium:
            cls.direct_medium = cls.env['utm.medium'].create({'name': 'Direct'})
            cls.env['ir.model.data'].create({
                'name': 'utm_medium_direct',
                'module': 'utm',
                'model': 'utm.medium',
                'res_id': cls.direct_medium.id,
            })

        # --- Last call date---
        # Get necessary models
        cls.Lead = cls.env['crm.lead']
        cls.PhoneCall = cls.env['crm.phonecall']
        cls.CallResult = cls.env['phone.call.result']  # Assuming your custom result model

        # Create a mock call result for "Not Contacted"
        cls.not_contacted_result = cls.CallResult.create({
            'name': 'No Answer',
            'not_contacted': True,
        })

        # Create a mock call result for "Contacted"
        cls.contacted_result = cls.CallResult.create({
            'name': 'Interested',
            'not_contacted': False,
        })

        # Define base dates
        cls.today_dt = Datetime.now()
        cls.yesterday_dt = cls.today_dt - timedelta(days=1)
        cls.two_days_ago_dt = cls.today_dt - timedelta(days=2)

        # Create a test lead
        cls.test_lead = cls.Lead.create({
            'name': 'Test Lead for Last Call Date',
            'type': 'lead',
        })

    def test_assign_partner_by_email(self):
        """Test finding and assigning an existing partner by email."""
        lead = self.env['crm.lead'].create({
            'name': 'Lead with matching email',
            'type': 'opportunity',
            'email_from': 'test.email@example.com',
        })
        self.assertFalse(lead.partner_id, "Pre-condition: Lead should not have a partner.")

        # Execute the method
        lead.assign_partner()

        self.assertEqual(lead.partner_id, self.partner_by_email,
                         "The partner found by email should be assigned.")


    def test_assign_partner_by_phone(self):
        """Test finding and assigning an existing partner by phone when email does not match."""
        lead = self.env['crm.lead'].create({
            'name': 'Lead with matching phone',
            'type': 'opportunity',
            'email_from': 'non.matching.email@example.com', # Ensure email does not match anyone
            'phone': '+1122334455',
        })
        self.assertFalse(lead.partner_id, "Pre-condition: Lead should not have a partner.")

        # Execute the method
        lead.assign_partner()

        self.assertEqual(lead.partner_id, self.partner_by_phone,
                         "The partner found by phone should be assigned.")


    def test_create_new_partner_when_no_match(self):
        """Test that a new partner is created if no existing partner is found."""
        lead_data = {
            'name': 'Lead for a new partner',
            'type': 'opportunity',
            'contact_name': 'Brand New Contact',
            'email_from': 'brand.new@example.com',
            'phone': '+9988776655',
        }
        lead = self.env['crm.lead'].create(lead_data)
        partner_count_before = self.env['res.partner'].search_count([])

        # Execute the method
        # This will call the underlying _handle_partner_assignment(create_missing=True)
        lead.assign_partner()

        partner_count_after = self.env['res.partner'].search_count([])

        self.assertEqual(partner_count_after, partner_count_before + 1,
                         "A new partner should have been created.")
        self.assertTrue(lead.partner_id, "The new partner should be assigned to the lead.")
        self.assertEqual(lead.partner_id.name, lead_data['contact_name'],
                         "Partner name should match the lead's contact_name.")
        self.assertEqual(lead.partner_id.email, lead_data['email_from'],
                         "Partner email should match the lead's email_from.")
        self.assertEqual(lead.partner_id.phone, lead_data['phone'],
                         "Partner phone should match the lead's phone.")


    def test_validation_for_creation_error_no_name(self):
        """Test ValidationError is raised if there's not enough data to create a partner."""
        # Missing contact_name
        lead_no_name = self.env['crm.lead'].create({
            'name': 'Lead without contact name',
            'type': 'opportunity',
            'contact_name': False,
            'email_from': 'some.email@example.com',
            'phone': '+34666222333',
        })

        with self.assertRaises(ValidationError, msg="Should fail without a contact name."):
            lead_no_name.assign_partner()


    def test_validation_for_creation_error_with_contact_name_no_email_and_phone(self):
        """Test ValidationError is raised if there's not enough data to create a partner."""
        # Missing both email and phone
        lead = self.env['crm.lead'].create({
            'name': 'Lead with no contact details',
            'type': 'opportunity',
            'contact_name': 'A. Contact',
            'email_from': False,
            'phone': False,
        })

        with self.assertRaises(ValidationError, msg="Should fail without either email or phone."):
            lead.assign_partner()


    def test_do_nothing_if_partner_already_assigned(self):
        """Test the method does nothing if a partner is already linked."""
        lead = self.env['crm.lead'].create({
            'name': 'Lead that already has a partner',
            'type': 'opportunity',
            'partner_id': self.another_partner.id,
        })
        partner_count_before = self.env['res.partner'].search_count([])

        # Execute the method
        lead.assign_partner()

        partner_count_after = self.env['res.partner'].search_count([])

        self.assertEqual(partner_count_before, partner_count_after,
                         "No new partner should be created.")
        self.assertEqual(lead.partner_id, self.another_partner,
                         "The original partner should remain unchanged.")

    def test_default_medium(self):
        lead = self.env['crm.lead'].create({
            'name': 'Lead with matching email',
            'type': 'opportunity',
            'email_from': 'test.email@example.com',
        })

        self.assertEqual(lead.medium_id, self.direct_medium,
                         "The opportunity medium should be 'Direct'.")

        other_medium = self.env['utm.medium'].create({'name': 'Other medium'})
        lead = self.env['crm.lead'].create({
            'name': 'Lead with matching email',
            'type': 'opportunity',
            'email_from': 'test.email@example.com',
            'medium_id': other_medium.id,
        })
        self.assertNotEqual(lead.medium_id, self.direct_medium,
            "The opportunity medium should not be 'Direct'.")
        self.assertEqual(lead.medium_id, other_medium,
            "The opportunity medium should not be 'Other medium'.")

    # --- Last call date tests---
    def test_last_call_date_no_phone_calls(self):
        """ Lead with no associated phone calls should have False dates."""
        self.assertFalse(self.test_lead.som_last_call_date,
                         "The Last Call Date should be False when there are no phone calls.")
        self.assertFalse(self.test_lead.som_last_call_date_only,
                         "The Last Call Date Only should be False when there are no phone calls.")


    def test_last_call_date_only_not_contacted_calls(self):
        """Lead with only 'Not Contacted' phone calls should have False dates."""
        # Create phone calls marked as 'not contacted'
        self.PhoneCall.create({
            'name': 'Call 1 - No Answer',
            'opportunity_id': self.test_lead.id,
            'date': self.today_dt,
            'som_phone_call_result_id': self.not_contacted_result.id,
        })
        self.PhoneCall.create({
            'name': 'Call 2 - No Answer',
            'opportunity_id': self.test_lead.id,
            'date': self.yesterday_dt,
            'som_phone_call_result_id': self.not_contacted_result.id,
        })

        # # Re-read the lead to force computation (not always necessary with 'store=True', but good practice)
        # self.test_lead.invalidate_cache(['som_last_call_date', 'som_last_call_date_only'])
        self.assertFalse(self.test_lead.som_last_call_date,
            "The Last Call Date should be False if all calls are 'Not Contacted'.")
        self.assertFalse(self.test_lead.som_last_call_date_only,
            "The Last Call Date Only should be False if all calls are 'Not Contacted'.")

    def test_last_call_date_single_contacted_call(self):
        """Lead with a single 'Contacted' call should reflect its date."""
        # Create a single successful call (Contacted)
        self.PhoneCall.create({
            'name': 'Call 1 - Interested',
            'opportunity_id': self.test_lead.id,
            'date': self.yesterday_dt,
            'som_phone_call_result_id': self.contacted_result.id,
        })

        # Check computed values
        self.assertEqual(self.test_lead.som_last_call_date, self.yesterday_dt,
                         "Last Call Date should match the date of the single contacted call.")
        self.assertEqual(self.test_lead.som_last_call_date_only, self.yesterday_dt.date(),
                         "Last Call Date Only should match the date part of the contacted call.")


    def test_last_call_date_multiple_calls_mixed_results(self):
        """Lead with multiple calls (contacted and not contacted),
            checking for the latest contacted one."""

        # 1. Oldest Contacted Call (should NOT be the result)
        self.PhoneCall.create({
            'opportunity_id': self.test_lead.id,
            'date': self.two_days_ago_dt,
            'som_phone_call_result_id': self.contacted_result.id,
            'name': 'Old Contacted Call',
        })

        # 2. Latest Not Contacted Call (should NOT be the result, even if newer)
        self.PhoneCall.create({
            'opportunity_id': self.test_lead.id,
            'date': self.today_dt,
            'som_phone_call_result_id': self.not_contacted_result.id,
            'name': 'Newest Not Contacted Call',
        })

        # 3. Last Contacted Call (should be the expected result)
        expected_last_call_dt = self.yesterday_dt
        self.PhoneCall.create({
            'opportunity_id': self.test_lead.id,
            'date': expected_last_call_dt,
            'som_phone_call_result_id': self.contacted_result.id,
            'name': 'Last Contacted Call',
        })

        self.assertEqual(self.test_lead.som_last_call_date, expected_last_call_dt,
            "Last Call Date should be the datetime of the latest contacted call.")
        self.assertEqual(
            self.test_lead.som_last_call_date_only, Date.to_date(expected_last_call_dt),
            "Last Call Date Only should be the date of the latest contacted call.")


    def test_last_call_date_update_call_result(self):
        """Changing the result of a phone call should trigger the computation."""
        # Create a call marked as 'not contacted' today
        call_to_update = self.PhoneCall.create({
            'name': 'Call to Update',
            'opportunity_id': self.test_lead.id,
            'date': self.today_dt,
            'som_phone_call_result_id': self.not_contacted_result.id,
        })

        # Initial check (should be False)
        self.assertFalse(self.test_lead.som_last_call_date)

        # Update the call result to 'contacted'
        call_to_update.som_phone_call_result_id = self.contacted_result.id
        self.assertEqual(self.test_lead.som_last_call_date, self.today_dt,
            "The date should update after changing a call to 'contacted'.")

    def test_last_call_date_update_call_date(self):
        """Changing the result of a phone call should trigger the computation."""
        # Create a call marked as 'not contacted' today
        call_to_update = self.PhoneCall.create({
            'name': 'Call to Update',
            'opportunity_id': self.test_lead.id,
            'date': self.yesterday_dt,
            'som_phone_call_result_id': self.contacted_result.id,
        })

        # Initial check
        self.assertEqual(self.test_lead.som_last_call_date, self.yesterday_dt,
            "The date should be yesterday")

        # Update the call result to 'contacted'
        call_to_update.date = self.today_dt
        self.assertEqual(self.test_lead.som_last_call_date, self.today_dt,
            "The date should update after changing a call date.")
