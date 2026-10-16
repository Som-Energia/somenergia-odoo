from psycopg2 import IntegrityError

from odoo.tests import common


class TestCommLog(common.TransactionCase):
    """Test comm.log model creation and constraints."""

    def setUp(self):
        super().setUp()
        self.partner = self.env.ref('base.res_partner_2')

    def test_create_log(self):
        """A basic comm.log is created with required fields."""
        log = self.env['comm.log'].create({
            'partner_id': self.partner.id,
            'subject': 'Test',
            'source_type': 'internal',
            'origin_app': 'odoo',
            'status': 'sent',
        })
        self.assertTrue(log)
        self.assertEqual(log.partner_id, self.partner)
        self.assertEqual(log.source_type, 'internal')
        self.assertEqual(log.origin_app, 'odoo')

    def test_default_values(self):
        """Defaults are applied when fields are omitted."""
        log = self.env['comm.log'].create({
            'partner_id': self.partner.id,
        })
        self.assertEqual(log.source_type, 'internal')
        self.assertEqual(log.origin_app, 'odoo')
        self.assertEqual(log.status, 'sent')
        self.assertEqual(log.lang, 'es_ES')

    def test_unique_per_partner_same_message(self):
        """Two logs for the same partner+message are rejected."""
        msg = self.env['mail.message'].create({
            'subject': 'Test',
            'body': '<p>test</p>',
            'model': 'res.partner',
            'res_id': self.partner.id,
            'message_type': 'comment',
        })
        self.env['comm.log'].create({
            'partner_id': self.partner.id,
            'source_type': 'internal',
            'origin_app': 'odoo',
            'status': 'sent',
            'source_message_id': msg.id,
        })
        with self.assertRaises(IntegrityError):
            self.env['comm.log'].create({
                'partner_id': self.partner.id,
                'source_type': 'internal',
                'origin_app': 'odoo',
                'status': 'sent',
                'source_message_id': msg.id,
            })

    def test_different_partner_same_message_allowed(self):
        """Two logs for different partners with the same message are allowed."""
        partner_a = self.partner
        partner_b = self.env['res.partner'].create({
            'name': 'Another Contact',
            'email': 'another@example.com',
        })
        msg = self.env['mail.message'].create({
            'subject': 'Shared',
            'body': '<p>shared</p>',
            'model': 'res.partner',
            'res_id': partner_a.id,
            'message_type': 'comment',
        })
        self.env['comm.log'].create({
            'partner_id': partner_a.id,
            'source_type': 'internal',
            'origin_app': 'odoo',
            'status': 'sent',
            'source_message_id': msg.id,
        })
        self.env['comm.log'].create({
            'partner_id': partner_b.id,
            'source_type': 'internal',
            'origin_app': 'odoo',
            'status': 'sent',
            'source_message_id': msg.id,
        })
        logs = self.env['comm.log'].search([('source_message_id', '=', msg.id)])
        self.assertEqual(len(logs), 2)


class TestCommLogPartnerScope(common.TransactionCase):
    """Test _get_partner_scope bidireccional logic."""

    def setUp(self):
        super().setUp()
        self.parent = self.env['res.partner'].create({
            'name': 'Parent Company',
            'email': 'parent@test.com',
        })
        self.child_1 = self.env['res.partner'].create({
            'name': 'Child One',
            'email': 'child1@test.com',
            'parent_id': self.parent.id,
        })
        self.child_2 = self.env['res.partner'].create({
            'name': 'Child Two',
            'email': 'child2@test.com',
            'parent_id': self.parent.id,
        })

    def test_no_children(self):
        """Without include_children, only the source partner is returned."""
        scope = self.env['comm.log']._get_partner_scope(self.parent, include_children=False)
        self.assertEqual(len(scope), 1)
        self.assertEqual(scope, self.parent)

    def test_parent_includes_children(self):
        """A parent includes all its children."""
        scope = self.env['comm.log']._get_partner_scope(self.parent, include_children=True)
        self.assertIn(self.parent, scope)
        self.assertIn(self.child_1, scope)
        self.assertIn(self.child_2, scope)

    def test_child_includes_parent_and_siblings(self):
        """A child includes parent and all siblings."""
        scope = self.env['comm.log']._get_partner_scope(self.child_1, include_children=True)
        self.assertIn(self.child_1, scope)
        self.assertIn(self.parent, scope)
        self.assertIn(self.child_2, scope)

    def test_no_duplicates(self):
        """No partner appears twice in the scope."""
        scope = self.env['comm.log']._get_partner_scope(self.parent, include_children=True)
        ids = [p.id for p in scope]
        self.assertEqual(len(ids), len(set(ids)))

    def test_standalone_partner(self):
        """A partner without children or parent returns only itself."""
        standalone = self.env['res.partner'].create({
            'name': 'Standalone',
            'email': 'stand@test.com',
        })
        scope = self.env['comm.log']._get_partner_scope(standalone, include_children=True)
        self.assertEqual(len(scope), 1)
        self.assertEqual(scope, standalone)
