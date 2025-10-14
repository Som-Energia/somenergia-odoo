# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('som_phonecall')
class TestPhonecal(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Get necessary models
        cls.PhoneCall = cls.env['crm.phonecall']
        cls.Lead = cls.env['crm.lead']
        cls.Partner = cls.env['res.partner']

        # Create a Partner to be assigned
        cls.test_partner = cls.Partner.create({
            'name': 'Test Partner S.A.',
            'is_company': True,
        })

        # Create an Opportunity linked to the Partner
        cls.test_opportunity = cls.Lead.create({
            'name': 'Partnered Opportunity',
            'type': 'opportunity',
            'partner_id': cls.test_partner.id,
        })

        # Create a second, unlinked partner
        cls.unrelated_partner = cls.Partner.create({'name': 'Unrelated Contact'})

    def test_assign_partner_successful(self):
        """Phonecall with opportunity and missing partner should be updated."""

        # 1. Create a Phonecall meeting all assignment criteria:
        #    - opportunity_id != False
        #    - partner_id = False
        #    - opportunity_id.partner_id != False
        phonecall_to_assign = self.PhoneCall.create({
            'name': 'Call to Assign',
            'opportunity_id': self.test_opportunity.id,
            'partner_id': False, # Explicitly set to False
        })

        # Initial check
        self.assertFalse(
            phonecall_to_assign.partner_id,
            "Pre-condition failed: partner_id should be False initially.")

        # Execute the function to be tested
        # We call the method directly on the PhoneCall model
        self.PhoneCall._assign_partner_with_opportunity()

        # Final check
        self.assertEqual(phonecall_to_assign.partner_id, self.test_partner,
                         "The partner_id was not correctly assigned from the opportunity.")

    def test_assign_partner_no_opportunity(self):
        """Phonecalls that do NOT meet criteria should NOT be modified."""

        # Phonecall NOT linked to any Opportunity
        pc_no_opp = self.PhoneCall.create({
            'name': 'No Opportunity',
            'opportunity_id': False,
            'partner_id': False,
        })

        # Execute the function
        self.PhoneCall._assign_partner_with_opportunity()

        # Check that none of the excluded calls were modified

        # No opportunity -> should remain False
        self.assertFalse(pc_no_opp.partner_id,
                         "Call with no opportunity should not be modified.")

    def test_assign_partner_already_has_a_partner(self):
        # Phonecall already HAS a Partner (even if it differs from the Opportunity's partner)
        pc_already_partnered = self.PhoneCall.create({
            'name': 'Already Partnered',
            'opportunity_id': self.test_opportunity.id,
            'partner_id': self.unrelated_partner.id,
        })

        # Execute the function
        self.PhoneCall._assign_partner_with_opportunity()

        # Already has a partner -> should keep the existing partner
        self.assertEqual(pc_already_partnered.partner_id, self.unrelated_partner,
            "Call already having a partner should not be overwritten.")

    def test_assign_partner_opp_no_partner(self):
         # Phonecall linked to an Opportunity that DOES NOT HAVE a Partner
        opp_no_partner = self.Lead.create({
            'name': 'Opportunity without Partner',
            'type': 'opportunity',
            'partner_id': False
        })
        pc_opp_no_partner = self.PhoneCall.create({
            'name': 'Opp without Partner',
            'opportunity_id': opp_no_partner.id,
            'partner_id': False,
        })

        self.PhoneCall._assign_partner_with_opportunity()

        # Opp has no partner -> should remain False
        self.assertFalse(pc_opp_no_partner.partner_id,
                         "Call whose opportunity has no partner should not be modified.")
