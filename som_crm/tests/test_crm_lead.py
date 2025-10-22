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

        # Get the activity types we will use
        cls.email_activity_type = cls.env.ref('mail.mail_activity_data_email')
        cls.todo_activity_type = cls.env.ref('mail.mail_activity_data_todo')

        # Get the message subtype for "Activity"
        # Messages for completed activities use this subtype
        cls.activity_subtype = cls.env.ref('mail.mt_activities')

        # We need a user to be the author of the messages
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test Call Center User',
            'login': 'test_cc_user',
            'email': 'test@ccuser.com',
            'som_call_center_user': 'call_center_1',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })

    def _create_done_activity_message(self, lead, activity_type, date_str):
        """
        Helper function to simulate a "completed activity" message.

        This is what your `_get_last_activity_done_by_type` function
        searches for in the lead's `message_ids`.
        """
        test_date = Datetime.from_string(date_str)
        return self.env['mail.message'].create({
            'model': 'crm.lead',
            'res_id': lead.id,
            'body': f'Simulation of completed activity {activity_type.name}.',
            'message_type': 'notification',
            'subtype_id': self.activity_subtype.id,
            'mail_activity_type_id': activity_type.id,
            'date': test_date,
            'author_id': self.test_user.partner_id.id,
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

    def test_default_channel(self):
        lead = self.env['crm.lead'].create({
            'name': 'Lead with matching email',
            'type': 'opportunity',
            'email_from': 'test.email@example.com',
        })

        self.assertEqual(lead.som_channel, self.direct_medium,
                         "The opportunity channel should be 'Direct'.")

        other_medium = self.env['utm.medium'].create({'name': 'Other medium'})
        lead = self.env['crm.lead'].create({
            'name': 'Lead with matching email',
            'type': 'opportunity',
            'email_from': 'test.email@example.com',
            'som_channel': other_medium.id,
        })
        self.assertNotEqual(lead.som_channel, self.direct_medium,
            "The opportunity channel should not be 'Direct'.")
        self.assertEqual(lead.som_channel, other_medium,
            "The opportunity channel should not be 'Other medium'.")

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

    # --- UTM processing tests---
    def test_utm_data_creation_and_update(self):
        """
        Test the complete flow: lead creation, URL processing, and field update.
        Verifies MTM priority and creation of new UTM records.
        """
        url = 'https://test.com/?mtm_campaign=NEW_CAMP_MTM&utm_campaign=OLD_CAMP&mtm_medium=EMAIL&utm_source=INSTA'

        # Create a lead with the URL
        lead = self.Lead.create({
            'name': 'Test Lead for UTM',
            'som_url_origin': url,
        })

        #Execute the processing function on the recordset
        lead.process_utm_data()

        # Verify Campaign (Should use MTM_CAMPAIGN)
        self.assertTrue(lead.campaign_id, "Campaign should be set.")
        self.assertEqual(lead.campaign_id.name, 'NEW_CAMP_MTM',
            "MTM parameter should take precedence and be created.")

        # Verify Medium (Should use MTM_MEDIUM)
        self.assertTrue(lead.medium_id, "Medium should be set.")
        self.assertEqual(lead.medium_id.name, 'EMAIL',
            "Medium should be created.")

        # Verify Source (Should use UTM_SOURCE)
        self.assertTrue(lead.source_id, "Source should be set.")
        self.assertEqual(lead.source_id.name, 'INSTA',
            "UTM parameter should be used as fall-back for Source.")


    def test_utm_data_reuse_existing_records(self):
        """
        Test that the function reuses existing UTM records.
        """
        campaign_name = 'Existing_Advert'
        medium_name = 'Existing_Web'
        source_name = 'Existing_Social'

        # Pre-create the records
        existing_campaign = self.env['utm.campaign'].create({'name': campaign_name})
        existing_medium = self.env['utm.medium'].create({'name': medium_name})
        existing_source = self.env['utm.source'].create({'name': source_name})

        # reate lead with URL referencing existing records
        url = f'https://test.com/?utm_campaign={campaign_name}&mtm_medium={medium_name}&utm_source={source_name}'
        lead = self.Lead.create({
            'name': 'Reuse Test',
            'som_url_origin': url,
        })

        # 3. Execute processing
        lead.process_utm_data()

        # 4. VERIFICATIONS

        # Verify Campaign ID matches the existing one
        self.assertEqual(lead.campaign_id.id, existing_campaign.id,
            "Should reuse the existing Campaign record.")

        # Verify Medium ID matches the existing one
        self.assertEqual(lead.medium_id.id, existing_medium.id,
            "Should reuse the existing Medium record.")

        # Verify Source ID matches the existing one
        self.assertEqual(lead.source_id.id, existing_source.id,
            "Should reuse the existing Source record.")

        # Verify no duplicate was created for Campaign
        self.assertEqual(self.env['utm.campaign'].search_count([('name', '=', campaign_name)]), 1,
            "A duplicate Campaign record should not be created.")

        # Verify no duplicate was created for Medium
        self.assertEqual(self.env['utm.medium'].search_count([('name', '=', medium_name)]), 1,
            "A duplicate Medium record should not be created.")

        # Verify no duplicate was created for Source
        self.assertEqual(self.env['utm.source'].search_count([('name', '=', source_name)]), 1,
            "A duplicate Source record should not be created.")

    def test_utm_data_partial_data(self):
        """
        Test with a URL that only contains data for Campaign. Source and Medium must be empty.
        """
        url = 'https://test.com/?utm_campaign=ONLY_CAMP'

        # 1. Create lead
        lead = self.Lead.create({
            'name': 'Partial Test',
            'som_url_origin': url,
        })

        # 2. Execute processing
        lead.process_utm_data()

        # 3. VERIFICATIONS
        self.assertTrue(lead.campaign_id, "Campaign ID should be set.")
        self.assertFalse(lead.medium_id, "Medium ID should be False/empty.")
        self.assertFalse(lead.source_id, "Source ID should be False/empty.")

        self.assertEqual(lead.campaign_id.name, 'ONLY_CAMP')

    def test_utm_data_no_url_origin_skip(self):
        """
        Test that leads with no som_url_origin are skipped by the filtered call.
        """
        # 1. Create a lead without URL
        lead = self.Lead.create({
            'name': 'No URL Test',
            'som_url_origin': False,
        })

        # Set initial UTMs (should not be overwritten or changed)
        pre_existing_campaign_id = self.env['utm.campaign'].create({'name': 'Pre-existing'})
        lead.write({
            'campaign_id': pre_existing_campaign_id.id,
        })
        initial_campaign_id = lead.campaign_id

        # Execute processing
        lead.process_utm_data()

        # The campaign_id should remain unchanged
        self.assertEqual(lead.campaign_id, initial_campaign_id,
            "The lead should have been skipped and its campaign_id unchanged.")

    # --- Last activity mail done date ---
    def test_lead_with_no_activities(self):
        """
        Test that a new lead with no activities has False in the fields.
        """
        # 1. Create a test lead
        lead = self.env['crm.lead'].create({'name': 'Lead with no activities'})

        # 2. Check the values
        self.assertFalse(
            lead.som_last_act_done_mail_date,
            "The Datetime field should be False if there are no activities."
        )
        self.assertFalse(
            lead.som_last_act_done_mail_date_only,
            "The Date field should be False if there are no activities."
        )

    def test_lead_with_other_activity_type(self):
        """
        Test that a lead with activities of ANOTHER type (e.g., Call)
        does not fill the 'Email' fields.
        """
        # 1. Create a test lead
        lead = self.env['crm.lead'].create({'name': 'Lead with call'})

        # 2. Create a "Call" completed activity message
        self._create_done_activity_message(
            lead,
            self.todo_activity_type,
            '2025-10-10 10:00:00'
        )

        # 3. Check the values
        self.assertFalse(
            lead.som_last_act_done_mail_date,
            "The Datetime field should be False if there are only calls."
        )
        self.assertFalse(
            lead.som_last_act_done_mail_date_only,
            "The Date field should be False if there are only calls."
        )


    def test_lead_with_one_email_activity(self):
        """
        Test that a lead with ONE 'Email' activity
        populates the fields correctly.
        """
        # 1. Create a test lead
        lead = self.env['crm.lead'].create({'name': 'Lead with 1 Email'})

        # 2. Define dates and create the message
        test_datetime_str = '2025-10-15 14:30:00'
        test_datetime = Datetime.from_string(test_datetime_str)
        test_date = test_datetime.date()

        self._create_done_activity_message(
            lead,
            self.email_activity_type,
            test_datetime_str
        )

        # 3. Check the values
        self.assertEqual(
            lead.som_last_act_done_mail_date,
            test_datetime,
            "The Datetime field must match the activity's date."
        )
        self.assertEqual(
            lead.som_last_act_done_mail_date_only,
            test_date,
            "The Date field must match the activity's date."
        )

    def test_lead_with_multiple_mixed_activities(self):
        """
        Test that a lead with multiple activities (Emails and Tasks)
        finds the date of the LAST 'Email'.
        """
        # 1. Create a test lead
        lead = self.env['crm.lead'].create({'name': 'Lead with mixed activities'})

        # 2. Create several activity messages

        # Old Email activity
        self._create_done_activity_message(
            lead,
            self.email_activity_type,
            '2025-10-01 12:00:00'
        )

        # Old TODO activity
        self._create_done_activity_message(
            lead,
            self.todo_activity_type,
            '2025-10-05 12:00:00'
        )

        # The most recent activity email (the one it should find)
        latest_email_str = '2025-10-10 18:00:00'
        self._create_done_activity_message(
            lead,
            self.email_activity_type,
            latest_email_str
        )

        # A task that is more recent than the last email (to test the filter)
        self._create_done_activity_message(
            lead,
            self.todo_activity_type,
            '2025-10-15 09:00:00'
        )

        # 3. Define the expected values
        expected_datetime = Datetime.from_string(latest_email_str)
        expected_date = expected_datetime.date()

        # 4. Check the values
        self.assertEqual(
            lead.som_last_act_done_mail_date,
            expected_datetime,
            "The Datetime field must be from the *last* email."
        )
        self.assertEqual(
            lead.som_last_act_done_mail_date_only,
            expected_date,
            "The Date field must be from the *last* email."
        )


@tagged('som_lead_upcoming_activities')
class TestCrmLeadUpcomingActivities(TransactionCase):
    """
    Test class for automatic activity creation in crm.lead.
    Tests both the date calculation and the batch creation logic.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Get necessary environments and today's date
        cls.Lead = cls.env['crm.lead']
        cls.Activity = cls.env['mail.activity']
        cls.today = Date.today()

        # 1. Prepare external data (Mocks/References)

        # Assuming the XML ID exists in your module.
        # We need to simulate the activity type and the 'won' stage.
        cls.activity_type = cls.env.ref(
            'som_crm.som_upcoming_activity', raise_if_not_found=False
        )
        if not cls.activity_type:
            # Create a dummy one if it doesn't exist for testing environment
            cls.activity_type = cls.env['mail.activity.type'].create({
                'name': 'Upcoming Activity Test',
                'res_model_id': cls.env.ref('crm.model_crm_lead').id,
                'category': 'default',
                'xml_id': 'som_crm.som_upcoming_activity'
            })

        # Get the 'Won' stage (assuming get_won_stage uses the standard Odoo XML ID)
        cls.won_stage = cls.env['crm.lead'].get_won_stage()

        # We need a user to be the author of the messages
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test Call Center User',
            'login': 'test_cc_user',
            'email': 'test@ccuser.com',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })

        # 2. Prepare Stages for date calculation tests
        # Stage A: No activity days configured
        cls.stage_a = cls.env['crm.stage'].create({
            'name': 'Stage A (No Days)',
            'sequence': 1,
            'som_upcoming_activity_days': 0, # Should return today
        })

        # Stage B: Activity scheduled 7 days out
        cls.stage_b = cls.env['crm.stage'].create({
            'name': 'Stage B (7 Days)',
            'sequence': 2,
            'som_upcoming_activity_days': 7,
        })

        # 3. Prepare Leads (Data for testing _create_upcoming_activities)

        # Lead 1: Candidate for activity creation (Stage A, No existing activity)
        cls.lead_1 = cls.Lead.create({
            'name': 'Candidate Lead',
            'stage_id': cls.stage_a.id,
            'user_id': cls.test_user.id,
        })

        # Lead 2: Excluded (Already has an activity)
        cls.lead_2 = cls.Lead.create({
            'name': 'Lead with Existing Activity',
            'stage_id': cls.stage_b.id,
            'user_id': cls.test_user.id,
        })
        # Create an existing activity to exclude Lead 2
        cls.Activity.create({
            'res_model_id': cls.env.ref('crm.model_crm_lead').id,
            'res_model': 'crm.lead',
            'res_id': cls.lead_2.id,
            'activity_type_id': cls.activity_type.id,
            'date_deadline': cls.today + timedelta(days=1),
            'user_id': cls.test_user.id,
        })

        # Lead 3: Excluded (Won stage)
        cls.lead_3 = cls.Lead.create({
            'name': 'Won Lead',
            'stage_id': cls.won_stage.id,
            'user_id': cls.test_user.id,
        })

        # Lead 4: Excluded (No assigned user)
        cls.lead_4 = cls.Lead.create({
            'name': 'Unassigned Lead',
            'stage_id': cls.stage_b.id,
            'user_id': False,
        })

        # Lead 5: Candidate for activity creation (Stage B, No existing activity)
        cls.lead_5 = cls.Lead.create({
            'name': 'Candidate Lead 2',
            'stage_id': cls.stage_b.id,
            'user_id': cls.test_user.id,
        })

    # -------------------------------------------------------------------------
    # Test for _get_next_activity_date
    # -------------------------------------------------------------------------

    def test_get_next_activity_date_no_days(self):
        """
        Test date calculation when stage days is 0 (should return today).
        """
        # Change lead stage to Stage A (0 days)
        self.lead_1.stage_id = self.stage_a

        expected_date = self.today + timedelta(days=0)
        calculated_date = self.lead_1._get_next_activity_date()

        self.assertEqual(calculated_date, expected_date,
                         "Date should be today if stage days is 0.")

    def test_get_next_activity_date_seven_days(self):
        """
        Test date calculation when stage days is 7.
        """
        # Change lead stage to Stage B (7 days)
        self.lead_1.stage_id = self.stage_b

        expected_date = self.today + timedelta(days=7)
        calculated_date = self.lead_1._get_next_activity_date()

        self.assertEqual(calculated_date, expected_date,
                         "Date should be 7 days from today.")

    def test_get_next_activity_date_no_stage(self):
        """
        Test date calculation when the lead has no stage (should return False).
        """
        # Remove stage from lead (should be rare, but good to test)
        self.lead_1.stage_id = False

        calculated_date = self.lead_1._get_next_activity_date()

        self.assertFalse(calculated_date,
                         "Date should be False if the lead has no stage.")

    # -------------------------------------------------------------------------
    # Test for _create_upcoming_activities
    # -------------------------------------------------------------------------

    def test_create_upcoming_activities_success(self):
        """
        Test the batch creation process: should create activities only for
        Lead 1 and Lead 5, and use the correct deadline.
        """
        initial_activity_count = self.Activity.search_count([('res_model', '=', 'crm.lead'),])

        #Initial check: Only Lead 2 has an activity
        initial_lead2_activity_count = self.Activity.search_count([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.lead_2.id),
        ])
        self.assertEqual(initial_lead2_activity_count, 1,
                         "Initial setup error: Only 1 activity should exist for Lead 2.")

        # 2. Run the activity creation method (called on the crm.lead model)
        self.Lead._create_upcoming_activities()

        # 3. Final check: Two new activities should have been created (Lead 1 and Lead 5)
        final_activity_count = self.Activity.search_count([('res_model', '=', 'crm.lead')])
        self.assertEqual(final_activity_count, initial_activity_count + 2,
                         "Should have created 2 new activities.")

        # 4. Verify activities for Lead 1 (Stage A -> 0 days)
        activity_lead_1 = self.Activity.search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.lead_1.id),
        ])
        self.assertTrue(activity_lead_1, "Activity must be created for Lead 1.")
        self.assertEqual(activity_lead_1.date_deadline, self.today,
                         "Lead 1 activity date should be today (0 days).")

        # 5. Verify activities for Lead 5 (Stage B -> 7 days)
        activity_lead_5 = self.Activity.search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.lead_5.id),
        ])
        self.assertTrue(activity_lead_5, "Activity must be created for Lead 5.")
        self.assertEqual(activity_lead_5.date_deadline, self.today + timedelta(days=7),
                         "Lead 5 activity date should be 7 days from today.")

    def test_create_upcoming_activities_exclusion(self):
        """
        Test that excluded leads (Won, Assigned, or without user) do NOT get an activity.
        """
        initial_lead2_activity_count = self.Activity.search_count([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.lead_2.id),
        ])

        # Run the creation method
        self.Lead._create_upcoming_activities()

        # Check exclusion: Lead 2 (Has activity)
        final_lead2_activity_count = self.Activity.search_count([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.lead_2.id),
        ])
        self.assertEqual(initial_lead2_activity_count, final_lead2_activity_count,
            "Lead 2 should not get a new activity (already has one).")

        # Check exclusion: Lead 3 (Won stage)
        activity_lead_3 = self.Activity.search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.lead_3.id),
        ])
        self.assertFalse(activity_lead_3, "Lead 3 should not get an activity (Won stage).")

        # Check exclusion: Lead 4 (No assigned user)
        activity_lead_4 = self.Activity.search([
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.lead_4.id),
        ])
        self.assertFalse(activity_lead_4, "Lead 4 should not get an activity (No assigned user).")
