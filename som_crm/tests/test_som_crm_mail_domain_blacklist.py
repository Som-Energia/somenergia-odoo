# -*- coding: utf-8 -*-
import uuid

from odoo.tests.common import TransactionCase, tagged
from odoo.addons.iap.tools.iap_tools import _MAIL_DOMAIN_BLACKLIST
from odoo.addons.som_crm.models.som_crm_mail_domain_blacklist import _ORIGINAL_MAIL_DOMAIN_BLACKLIST


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

    def test_unlink_keeps_original_blacklist_domain(self):
        """
        Deleting a custom record must not remove a domain already present in the original blacklist.
        """

        domain_name = next(iter(_ORIGINAL_MAIL_DOMAIN_BLACKLIST))

        record = self.env['som.crm.mail.domain.blacklist'].create({'name': domain_name})
        record.unlink()

        self.assertIn(
            domain_name,
            _MAIL_DOMAIN_BLACKLIST,
            "Original blacklist domains must stay in memory after unlink.")

    def test_write_updates_blacklist(self):
        """
        Test that updating the domain name through write also updates
        the global _MAIL_DOMAIN_BLACKLIST.
        """

        original_domain = 'test-write-domain.cat'
        new_domain = 'test-updated-domain.cat'

        if original_domain in _MAIL_DOMAIN_BLACKLIST:
            _MAIL_DOMAIN_BLACKLIST.remove(original_domain)
        if new_domain in _MAIL_DOMAIN_BLACKLIST:
            _MAIL_DOMAIN_BLACKLIST.remove(new_domain)

        record = self.env['som.crm.mail.domain.blacklist'].create({'name': original_domain})
        self.assertIn(
            original_domain,
            _MAIL_DOMAIN_BLACKLIST,
            "The original domain should be in the blacklist after creation.")

        record.write({'name': new_domain})
        self.assertNotIn(
            original_domain,
            _MAIL_DOMAIN_BLACKLIST,
            "The original domain should be removed from the blacklist after update.")
        self.assertIn(
            new_domain,
            _MAIL_DOMAIN_BLACKLIST,
            "The new domain should be added to the blacklist after update.")

    def test_write_keeps_original_blacklist_domain(self):
        """
        Updating a record must not remove the previous value if it belongs to the original blacklist
        """

        original_domain = next(iter(_ORIGINAL_MAIL_DOMAIN_BLACKLIST))
        new_domain = 'test-original-domain-update.cat'

        if new_domain in _MAIL_DOMAIN_BLACKLIST:
            _MAIL_DOMAIN_BLACKLIST.remove(new_domain)

        record = self.env['som.crm.mail.domain.blacklist'].create({'name': original_domain})
        record.write({'name': new_domain})

        self.assertIn(
            original_domain,
            _MAIL_DOMAIN_BLACKLIST,
            "Original blacklist domains must stay in memory after write.")
        self.assertIn(
            new_domain,
            _MAIL_DOMAIN_BLACKLIST,
            "The updated domain should be added to the blacklist after write.")
