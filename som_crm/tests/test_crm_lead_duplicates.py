# -*- coding: utf-8 -*-

import uuid

from odoo.tests.common import TransactionCase, tagged


@tagged('som_lead_duplicates')
class TestCrmLeadDuplicates(TransactionCase):

    def _create_lead(self, email_from):
        return self.env['crm.lead'].create({
            'name': f'Lead {email_from}',
            'type': 'lead',
            'email_from': email_from,
        })

    def test_compute_potential_duplicates_domain_search_non_blacklisted(self):
        """For non-blacklisted domains, duplicates are searched by domain."""
        token = uuid.uuid4().hex[:8]
        domain = f'somdup-{token}.invalid'

        lead_a = self._create_lead(f'alice-{token}@{domain}')
        lead_b = self._create_lead(f'bob-{token}@{domain}')

        self.assertIn(
            lead_b,
            lead_a.duplicate_lead_ids,
            'Expected duplicate by shared non-blacklisted domain.',
        )
        self.assertGreaterEqual(lead_a.duplicate_lead_count, 1)

    def test_compute_potential_duplicates_blacklisted_domain_is_exact_email(self):
        """For blacklisted domains, duplicates are searched by exact email."""
        from odoo.addons.iap.tools.iap_tools import _MAIL_DOMAIN_BLACKLIST

        self.assertIn('xtec.cat', _MAIL_DOMAIN_BLACKLIST)

        token = uuid.uuid4().hex[:8]
        lead_a = self._create_lead(f'alice-{token}@xtec.cat')
        lead_b = self._create_lead(f'bob-{token}@xtec.cat')

        self.assertNotIn(
            lead_b,
            lead_a.duplicate_lead_ids,
            'Blacklisted domains should not match by domain-only search.',
        )
        self.assertEqual(lead_a.duplicate_lead_count, 0)
