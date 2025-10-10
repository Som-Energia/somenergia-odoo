# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError

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
