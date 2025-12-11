# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('som_lead_fetchmail')
class TestCrmLeadFetchmail(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestCrmLeadFetchmail, cls).setUpClass()

        # --- Create necessary records for the tests ---
        # 1. Sales Team User
        cls.sales_user = cls.env['res.users'].create({
            'name': 'Sales User',
            'login': 'sales_user',
            'email': 'sales@test.com',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })
        cls.sales_user.action_create_employee()

        # 2. Sales Team
        cls.sales_team = cls.env.ref(
            'sales_team.team_sales_department', raise_if_not_found=False
        ) or False
        if not cls.sales_team:
            cls.sales_team = cls.env['crm.team'].create({
                'name': 'Sales Department',
                # 'user_id': cls.sales_user.id,
            })
            # Create an XML ID for the team to be found by self.env.ref()
            cls.env['ir.model.data'].create({
                'name': 'team_sales_department',
                'module': 'sales_team',
                'model': 'crm.team',
                'res_id': cls.sales_team.id,
            })
        cls.sales_team.user_id = cls.sales_user

        # 3. UTM Medium
        cls.webform_medium = cls.env.ref(
            'som_crm.som_medium_webform', raise_if_not_found=False
        ) or False
        if not cls.webform_medium:
            cls.webform_medium = cls.env['utm.medium'].create({'name': 'Web Form'})
            # Create an XML ID for the medium to be found by self.env.ref()
            cls.env['ir.model.data'].create({
                'name': 'som_medium_webform',
                'module': 'som_crm',
                'model': 'utm.medium',
                'res_id': cls.webform_medium.id,
            })

        # 4. Another users for testing edge cases
        cls.other_user = cls.env['res.users'].create({
            'name': 'Other Test User',
            'login': 'other_user',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })

        cls.team_user = cls.env['res.users'].create({
            'name': 'team User',
            'login': 'team_user',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })

        # Team with members
        cls.sales_team.write({
            'crm_team_member_ids': [
                (0, 0, {'user_id': cls.sales_user.id}),
                (0, 0, {'user_id': cls.team_user.id}),
            ],
        })

        # --- Define the context that triggers the fetchmail logic ---
        cls.fetchmail_context = {
            'fetchmail_cron_running': True,
            'default_fetchmail_server_id': 1,  # The ID can be any truthy value
        }

        cls.company = cls.env.ref('base.main_company')
        cls.company.write({
            'som_ff_auto_upcomming_activity': True,
        })


    def test_lead_creation_with_fetchmail_context_team_leader(self):
        """
        Test that a lead created with the fetchmail context gets the correct user and medium.
        """
        lead = self.env['crm.lead'].with_context(**self.fetchmail_context).create({
            'name': 'Lead from Fetchmail',
            'type': 'opportunity',
            'user_id': False,
        })

        # --- Asserts ---
        self.assertTrue(lead.user_id, "The lead should have a user assigned.")
        self.assertNotEqual(lead.user_id, self.sales_user,
                         "The lead should not have the team leader user assigned.")
        self.assertEqual(lead.som_channel, self.webform_medium,
                         "The lead's medium should be set to 'Web Form'.")
        self.assertEqual(len(lead.activity_ids), 1,
                         "The lead should have one activity scheduled.")

    def test_lead_creation_with_fetchmail_context_no_team_leader(self):
        """
        Test that a lead created with the fetchmail context gets the correct user and medium.
        """
        self.sales_team.write({
            'crm_team_member_ids': [(5, 0, 0)],  # Remove all members
            'user_id': False,  # Remove team leader
        })

        self.sales_team.write({
            'crm_team_member_ids': [
                (0, 0, {'user_id': self.sales_user.id}),
            ],
        })  # Add only the sales_user as member

        lead = self.env['crm.lead'].with_context(**self.fetchmail_context).create({
            'name': 'Lead from Fetchmail',
            'type': 'opportunity',
            'user_id': False,
        })

        # --- Asserts ---
        self.assertTrue(lead.user_id, "The lead should have a user assigned.")
        self.assertEqual(lead.user_id, self.sales_user,
                         "The lead should have the sales user assigned.")
        self.assertNotEqual(lead.user_id, self.team_user,
                         "The lead should not have the team user assigned.")
        self.assertEqual(lead.som_channel, self.webform_medium,
                         "The lead's medium should be set to 'Web Form'.")
        self.assertEqual(len(lead.activity_ids), 1,
                         "The lead should have one activity scheduled.")

    def test_lead_creation_without_fetchmail_context(self):
        """
        Test that a lead created without the special context is not modified.
        """
        lead = self.env['crm.lead'].create({
            'name': 'Standard Lead',
            'type': 'opportunity',
        })

        # --- Asserts ---
        self.assertNotEqual(lead.user_id, self.sales_user,
            "The lead should not have the team leader user assigned.")
        self.assertNotEqual(lead.som_channel, self.webform_medium,
            "The lead should not have the webform medium.")

    def test_fetchmail_context_respects_existing_user(self):
        """
        Test that if a lead is created with a user, the fetchmail logic does not override it.
        """
        lead = self.env['crm.lead'].with_context(**self.fetchmail_context).create({
            'name': 'Lead from Fetchmail with existing user',
            'type': 'opportunity',
            'user_id': self.other_user.id,
        })

        # --- Asserts ---
        self.assertEqual(lead.user_id, self.other_user,
                         "The existing user should not be overridden by the fetchmail logic.")
        self.assertEqual(lead.som_channel, self.webform_medium,
                         "The medium should still be assigned even if a user exists.")

    def test_missing_config_data_does_not_fail(self):
        """
        Test that the creation process does not raise an error if the ref'd records are not found.
        """
        self.sales_team.unlink()
        lead = self.env['crm.lead'].with_context(**self.fetchmail_context).create({
            'name': 'Lead with missing config',
            'type': 'opportunity',
            'user_id': False,
        })
        # --- Asserts ---
        self.assertFalse(
            lead.user_id, "User should not be assigned if team is not found.")
        self.assertEqual(lead.som_channel, self.webform_medium,
            "The medium should be the default one")
