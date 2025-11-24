# -*- coding: utf-8 -*-

import logging
from unittest.mock import patch, MagicMock, ANY

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import config

_logger = logging.getLogger(__name__)


@tagged('som_erp_lead_sync')
class TestErpLeadSync(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """
        Initial setup for the tests.
        Creates CRM stages and test leads.
        """
        super().setUpClass()
        cls.CrmStage = cls.env['crm.stage']
        cls.CrmLead = cls.env['crm.lead']

        # Create necessary stages
        cls.stage_new = cls.CrmStage.create({
            'name': 'New',
            'sequence': 1,
            'is_won': False,
        })

        cls.stage_won = cls.env['crm.lead'].get_won_stage()
        if not cls.stage_won:
            cls.stage_won = cls.CrmStage.create({
                'name': 'Won',
                'sequence': 10,
                'is_won': True,
            })

        # Create test leads
        cls.lead_to_find_by_cups = cls.CrmLead.create({
            'name': 'Lead to find by CUPS',
            'type': 'opportunity',
            'stage_id': cls.stage_new.id,
            'som_cups': 'ES0021000000000001ABCD',
            'vat': '',
            'email_from': '',
            'phone': '',
        })

        cls.lead_to_find_by_vat = cls.CrmLead.create({
            'name': 'Lead to find by VAT',
            'type': 'opportunity',
            'stage_id': cls.stage_new.id,
            'som_cups': '',
            'vat': 'B12345678',
            'email_from': 'test@example.com',
        })

        cls.lead_to_find_by_phone = cls.CrmLead.create({
            'name': 'Lead to find by Phone',
            'type': 'opportunity',
            'stage_id': cls.stage_new.id,
            'som_cups': '',
            'vat': '',
            'phone': '+34 600112233',
        })

        cls.lead_not_in_erp = cls.CrmLead.create({
            'name': 'Lead non existant in ERP',
            'type': 'opportunity',
            'stage_id': cls.stage_new.id,
            'som_cups': 'ES_NOT_IN_ERP',
        })

        cls.lead_already_won = cls.CrmLead.create({
            'name': 'Lead already won',
            'type': 'opportunity',
            'stage_id': cls.stage_won.id,
            'som_cups': 'ES_ALREADY_WON',
        })

        cls.lead_inactive_to_check = cls.CrmLead.create({
            'name': 'Lead Inactive to Check in ERP',
            'type': 'opportunity',
            'stage_id': cls.stage_new.id,
            'som_cups': 'ES_INACTIVE_LEAD',
            'active': False,
        })


    def test_get_won_stage(self):
        """Test that the 'Won' stage is correctly retrieved."""
        won_stage = self.CrmLead.get_won_stage()
        self.assertTrue(won_stage)
        self.assertEqual(won_stage.id, self.stage_won.id)

    def test_get_leads_to_check(self):
        """Test that the correct leads to check in the ERP are retrieved."""
        leads_to_check = self.CrmLead.get_leads_to_check(self.stage_won)

        # It should find the 3 leads that are not in the 'Won' stage
        self.assertIn(self.lead_to_find_by_cups, leads_to_check)
        self.assertIn(self.lead_to_find_by_vat, leads_to_check)
        self.assertIn(self.lead_not_in_erp, leads_to_check)
        self.assertIn(self.lead_to_find_by_phone, leads_to_check)

        # It should not include the lead that is already 'Won'
        self.assertNotIn(self.lead_already_won, leads_to_check)

    def test_erp_search_helpers(self):
        """
        Test the ERP search helper methods,
        verifying that they build the search domain correctly.
        """
        _logger.info("--> Test: test_erp_search_helpers")
        mock_erp_lead_obj = MagicMock()

        # Test _erp_search_by_cups
        self.CrmLead._erp_search_by_cups(
            mock_erp_lead_obj, [('id', '!=', 0)], 'ES0021000000000001ABCDEFGH'
        )
        mock_erp_lead_obj.search.assert_called_with(
            [('id', '!=', 0), ('cups', '=ilike', 'ES0021000000000001AB%')], limit=1
        )

        # Test _erp_search_by_vat (with and without 'ES' prefix)
        self.CrmLead._erp_search_by_vat(mock_erp_lead_obj, [], 'B12345678')
        mock_erp_lead_obj.search.assert_called_with(
            [('titular_vat', '=', 'ESB12345678')], limit=1
        )
        self.CrmLead._erp_search_by_vat(mock_erp_lead_obj, [], 'ESB12345678')
        mock_erp_lead_obj.search.assert_called_with(
            [('titular_vat', '=', 'ESB12345678')], limit=1
        )

        # Test _erp_search_by_email
        self.CrmLead._erp_search_by_email(mock_erp_lead_obj, [], 'test@example.com')
        mock_erp_lead_obj.search.assert_called_with([
            '|',
             ('titular_email', '=', 'test@example.com'),
             ('titular_email', '=', 'TEST@EXAMPLE.COM')
        ], limit=1)

        # Test _erp_search_by_phone
        self.CrmLead._erp_search_by_phone(mock_erp_lead_obj, [], '+34 600112233')
        mock_erp_lead_obj.search.assert_called_with(
            [('titular_phone', '=', '600112233')], limit=1
        )
        self.CrmLead._erp_search_by_phone(mock_erp_lead_obj, [], '933001122')
        mock_erp_lead_obj.search.assert_called_with(
            [('titular_phone', '=', '933001122')], limit=1
        )

    def test_get_contract_in_erp_priority(self):
        """
        Test the logic and search priority in 'get_contract_in_erp'.
        It should find by CUPS first, even if it has other data.
        """
        _logger.info("--> Test: test_get_contract_in_erp_priority")

        mock_erp_lead_obj = MagicMock()
        # We simulate that the search by CUPS finds an ID
        mock_erp_lead_obj.search.return_value = [101]

        # This lead has CUPS and VAT, but it must use CUPS due to priority
        lead_with_multiple_fields = self.CrmLead.create({
            'name': 'Lead with CUPS and VAT',
            'type': 'opportunity',
            'stage_id': self.stage_new.id,
            'som_cups': 'ES_PRIORITY_TEST',
            'vat': 'B87654321',
        })

        erp_id = lead_with_multiple_fields.get_contract_in_erp(mock_erp_lead_obj)

        self.assertEqual(erp_id, 101)
        # We verify that search was called with the CUPS domain
        mock_erp_lead_obj.search.assert_called_once_with(
            [('crm_lead_id', '=', 0), ('cups', '=ilike', 'ES_PRIORITY_TEST%')], limit=1
        )

    @patch('odoo.addons.som_crm.models.crm_lead.Client')
    def test_erp_sync_full_process(self, mock_erppeek_client):
        """
        Full test of the _erp_sync synchronization process.
        - Mocks the ERP connection.
        - Simulates the ERP response for different leads.
        - Verifies that the correct leads are moved to the 'Won' stage.
        """

        mock_client_instance = MagicMock()
        mock_erppeek_client.return_value = mock_client_instance

        mock_erp_lead_model = MagicMock()
        mock_client_instance.model.return_value = mock_erp_lead_model

        # Simulate ERP search behavior
        def search_side_effect(domain, limit):
            # Simulate search by CUPS
            if ('cups', '=ilike', 'ES0021000000000001AB%') in domain:
                return [101]  # ERP ID for lead_to_find_by_cups
            # Simulate search by VAT
            if ('titular_vat', '=', 'ESB12345678') in domain:
                return [102]  # ERP ID for lead_to_find_by_vat
            # Simulate search by phone
            if ('titular_phone', '=', '600112233') in domain:
                return [103] # ERP ID for lead_to_find_by_phone
            # For any other case (like lead_not_in_erp), return nothing
            return []

        mock_erp_lead_model.search.side_effect = search_side_effect

        # Execute the method to be tested
        self.CrmLead._erp_sync()

        # --- Assertions ---

        # 1. Verify that the found leads have been updated
        self.assertEqual(self.lead_to_find_by_cups.stage_id, self.stage_won)
        self.assertEqual(self.lead_to_find_by_cups.som_erp_lead_id, 101)

        self.assertEqual(self.lead_to_find_by_vat.stage_id, self.stage_won)
        self.assertEqual(self.lead_to_find_by_vat.som_erp_lead_id, 102)

        self.assertEqual(self.lead_to_find_by_phone.stage_id, self.stage_won)
        self.assertEqual(self.lead_to_find_by_phone.som_erp_lead_id, 103)

        # 2. Verify that the lead not found has not changed stage
        self.assertEqual(self.lead_not_in_erp.stage_id, self.stage_new)
        self.assertFalse(self.lead_not_in_erp.som_erp_lead_id)

        # 3. Verify that write was called on the ERP for the found leads
        mock_erp_lead_model.write.assert_any_call(
            101, {'crm_lead_id': self.lead_to_find_by_cups.id})
        mock_erp_lead_model.write.assert_any_call(
            102, {'crm_lead_id': self.lead_to_find_by_vat.id})
        mock_erp_lead_model.write.assert_any_call(
            103, {'crm_lead_id': self.lead_to_find_by_phone.id})
        self.assertEqual(mock_erp_lead_model.write.call_count, 3)


    def test_get_leads_to_check_include_inactive(self):
        """Test that inactive leads are included when include_inactive=True."""
        leads_exclude_inactive = self.CrmLead.get_leads_to_check(self.stage_won, include_inactive=False)
        self.assertNotIn(self.lead_inactive_to_check, leads_exclude_inactive)

        leads_include_inactive = self.CrmLead.get_leads_to_check(self.stage_won, include_inactive=True)
        self.assertIn(self.lead_to_find_by_cups, leads_include_inactive)
        self.assertIn(self.lead_to_find_by_vat, leads_include_inactive)
        self.assertIn(self.lead_not_in_erp, leads_include_inactive)
        self.assertIn(self.lead_to_find_by_phone, leads_include_inactive)
        self.assertIn(self.lead_inactive_to_check, leads_include_inactive)
        self.assertLess(len(leads_exclude_inactive), len(leads_include_inactive))

    @patch('odoo.addons.som_crm.models.crm_lead.Client')
    def test_erp_sync_with_inactive_lead(self, mock_erppeek_client):
        """
        Test _erp_sync with include_inactive=True to ensure inactive leads
        are checked, marked as 'Won', and set to active=True.
        """
        mock_client_instance = MagicMock()
        mock_erppeek_client.return_value = mock_client_instance
        mock_erp_lead_model = MagicMock()
        mock_client_instance.model.return_value = mock_erp_lead_model

        # Simulate ERP search behavior: only the inactive lead is found
        def search_side_effect(domain, limit):
            if ('cups', '=ilike', 'ES_INACTIVE_LEAD%') in domain:
                return [999]  # ERP ID for lead_inactive_to_check
            return []

        mock_erp_lead_model.search.side_effect = search_side_effect

        # Execute the method to be tested, specifically including inactive leads
        self.CrmLead._erp_sync(include_inactive=True)

        # --- Assertions ---

        # Verify that the lead was found and updated
        self.assertEqual(self.lead_inactive_to_check.stage_id, self.stage_won)
        self.assertEqual(self.lead_inactive_to_check.som_erp_lead_id, 999)

        # Verify that the lead is now active
        self.assertTrue(self.lead_inactive_to_check.active)

        # Verify that the ERP was updated
        mock_erp_lead_model.write.assert_called_once_with(
            999, {'crm_lead_id': self.lead_inactive_to_check.id})
