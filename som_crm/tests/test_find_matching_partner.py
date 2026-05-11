# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged


@tagged('som_find_matching_partner')
class TestFindMatchingPartner(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_with_email = cls.env['res.partner'].create({
            'name': 'Partner With Email',
            'email': 'existing@example.com',
            'phone': '600000000',
        })
        cls.partner_without_email = cls.env['res.partner'].create({
            'name': 'Partner Without Email',
            'phone': '611111111',
        })

    def _create_lead(self, phone=False, email_from=False):
        vals = {
            'name': 'Test Lead',
            'type': 'opportunity',
        }
        if phone:
            vals['phone'] = phone
        if email_from:
            vals['email_from'] = email_from
        return self.env['crm.lead'].create(vals)

    def test_match_by_email(self):
        """Lead with matching email finds partner by email."""
        lead = self._create_lead(email_from='existing@example.com')
        partner = lead._find_matching_partner_custom()
        self.assertEqual(partner, self.partner_with_email)

    def test_match_by_phone_no_emails(self):
        """Lead without email, partner without email: match by phone."""
        lead = self._create_lead(phone='611111111')
        partner = lead._find_matching_partner_custom()
        self.assertEqual(partner, self.partner_without_email)

    def test_match_by_phone_same_email(self):
        """Lead with same phone and same email as partner: match."""
        lead = self._create_lead(phone='600000000', email_from='existing@example.com')
        partner = lead._find_matching_partner_custom()
        self.assertEqual(partner, self.partner_with_email)

    def test_no_match_by_phone_different_email(self):
        """
        Lead with a fake phone (e.g. 600000000) and a different email than the matched partner:
        no match is returned to avoid assigning the wrong contact.
        """
        lead = self._create_lead(phone='600000000', email_from='other@example.com')
        partner = lead._find_matching_partner_custom()
        self.assertFalse(partner)

    def test_no_match_no_data(self):
        """Lead without email or phone: no match."""
        lead = self._create_lead()
        partner = lead._find_matching_partner_custom()
        self.assertFalse(partner)

    def test_match_by_phone_partner_no_email_lead_has_email(self):
        """Phone match: partner has no email but lead does — match proceeds."""
        lead = self._create_lead(phone='611111111', email_from='newperson@example.com')
        partner = lead._find_matching_partner_custom()
        self.assertEqual(partner, self.partner_without_email)
