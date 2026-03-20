# -*- coding: utf-8 -*-
import uuid

from odoo.tests.common import TransactionCase, tagged
from odoo.addons.iap.tools.iap_tools import _MAIL_DOMAIN_BLACKLIST


@tagged('som_mail_domain_blacklist')
class TestSomCrmMailDomainBlacklist(TransactionCase):

    def setUp(self):
        super(TestSomCrmMailDomainBlacklist, self).setUp()
        self.initial_blacklist = (
            _MAIL_DOMAIN_BLACKLIST.copy() if isinstance(_MAIL_DOMAIN_BLACKLIST, set) else set()
        )

    def tearDown(self):
        super(TestSomCrmMailDomainBlacklist, self).tearDown()
        if isinstance(_MAIL_DOMAIN_BLACKLIST, set):
            _MAIL_DOMAIN_BLACKLIST.clear()
            _MAIL_DOMAIN_BLACKLIST.update(self.initial_blacklist)

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
        self.env['som.crm.mail.domain.blacklist'].create({'name': 'xtec.cat'})

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

    def test_unlink_removes_from_blacklist(self):
        """Test that removing a domain from the blacklist
        model also removes it from the global _MAIL_DOMAIN_BLACKLIST."""

        domain_name = 'test-unlink-domain.cat'

        # Keep track if it existed before so we don't assume
        if domain_name in _MAIL_DOMAIN_BLACKLIST:
            _MAIL_DOMAIN_BLACKLIST.remove(domain_name)

        record = self.env['som.crm.mail.domain.blacklist'].create({'name': domain_name})
        self.assertIn(
            domain_name,
            _MAIL_DOMAIN_BLACKLIST,
            "The domain should be added to the blacklist upon creation.")

        record.unlink()
        self.assertNotIn(
            domain_name,
            _MAIL_DOMAIN_BLACKLIST,
            "The domain should be removed from the blacklist after unlink.")

    def test_unlink_keeps_duplicates(self):
        """Test that removing a domain doesn't remove it from the global _MAIL_DOMAIN_BLACKLIST
        if another record holds the same domain."""

        domain_name = 'test-duplicate-domain.cat'

        if domain_name in _MAIL_DOMAIN_BLACKLIST:
            _MAIL_DOMAIN_BLACKLIST.remove(domain_name)

        self.env['som.crm.mail.domain.blacklist'].create([
            {'name': domain_name},
            {'name': domain_name}
        ])

        record = self.env['som.crm.mail.domain.blacklist'].search([
            ('name', '=', domain_name),
        ], limit=1)
        record.unlink()

        self.assertIn(
            domain_name,
            _MAIL_DOMAIN_BLACKLIST,
            "The domain should still be in the blacklist because another record has it.")

        remaining_records = self.env['som.crm.mail.domain.blacklist'].search([
            ('name', '=', domain_name),
        ])
        remaining_records.unlink()

        self.assertNotIn(
            domain_name,
            _MAIL_DOMAIN_BLACKLIST,
            "The domain should be removed from the blacklist once all duplicates are unlinked.")
