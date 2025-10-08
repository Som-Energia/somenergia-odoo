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

        # 4. Another user for testing edge cases
        cls.other_user = cls.env['res.users'].create({
            'name': 'Other Test User',
            'login': 'other_user',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })

        # --- Define the context that triggers the fetchmail logic ---
        cls.fetchmail_context = {
            'fetchmail_cron_running': True,
            'default_fetchmail_server_id': 1,  # The ID can be any truthy value
        }

    def test_lead_creation_with_fetchmail_context(self):
        """
        Test that a lead created with the fetchmail context gets the correct user and medium.
        """
        lead = self.env['crm.lead'].with_context(**self.fetchmail_context).create({
            'name': 'Lead from Fetchmail',
            'type': 'opportunity',
            'user_id': False,
        })

        # --- Asserts ---
        self.assertEqual(lead.user_id, self.sales_user,
                         "The lead should be assigned to the sales team's user.")
        self.assertEqual(lead.medium_id, self.webform_medium,
                         "The lead's medium should be set to 'Web Form'.")

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
        self.assertNotEqual(lead.medium_id, self.webform_medium,
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
        self.assertEqual(lead.medium_id, self.webform_medium,
                         "The medium should still be assigned even if a user exists.")

    def test_missing_config_data_does_not_fail(self):
        """
        Test that the creation process does not raise an error if the ref'd records are not found.
        (by using raise_if_not_found=False).
        """
        # Check no sales team user
        self.sales_team.write({'user_id': False})
        lead = self.env['crm.lead'].with_context(**self.fetchmail_context).create({
            'name': 'Lead with missing config 2',
            'type': 'opportunity',
            'user_id': False,
        })

        # --- Asserts ---
        self.assertFalse(lead.user_id,
                         "User should not be assigned if team leader is not set.")
        self.assertEqual(lead.medium_id, self.webform_medium,
                         "The medium should still be assigned even if no team leader.")

        self.env['crm.team'].write({'user_id': self.sales_user.id})
        # We simulate this by temporarily renaming the XML IDs
        # This is a bit advanced, but shows how to test missing data scenarios
        webform_ref = self.env.ref('som_crm.som_medium_webform', raise_if_not_found=False)
        team_ref = self.env.ref('sales_team.team_sales_department', raise_if_not_found=False)

        # Temporarily "break" the references
        if webform_ref:
            webform_ref.write({'name':'som_medium_webform_disabled'})
        if team_ref:
            team_ref.write({'name': 'team_sales_department_disabled'})

        # This should now run without finding the records, and not raise an error
        try:
            lead = self.env['crm.lead'].with_context(**self.fetchmail_context).create({
                'name': 'Lead with missing config',
                'type': 'opportunity',
                'user_id': False,
            })
            # --- Asserts ---
            self.assertFalse(
                lead.user_id, "User should not be assigned if team is not found.")
            self.assertEqual(lead.medium_id, self.webform_medium,
                "The medium should be the default one")
        finally:
            # Clean up: restore the XML IDs to not affect other tests
            if webform_ref:
                webform_ref.name = 'som_medium_webform'
            if team_ref:
                team_ref.name = 'team_sales_department'
