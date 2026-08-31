from odoo.tests import common
from odoo.exceptions import ValidationError


class TestCommLogRule(common.TransactionCase):
    """Test comm.log.rule model and constraints."""

    def test_create_rule(self):
        """A basic rule can be created with valid model and field."""
        model = self.env['ir.model']._get('res.partner')
        rule = self.env['comm.log.rule'].create({
            'model_id': model.id,
            'partner_field_name': 'id',
            'include_child_contacts': True,
            'description': 'Test rule',
        })
        self.assertTrue(rule)
        self.assertTrue(rule.active)
        self.assertEqual(rule.model_id, model)

    def test_unique_model_constraint(self):
        """Two rules for the same model are rejected."""
        model = self.env['ir.model']._get('res.partner')
        self.env['comm.log.rule'].create({
            'model_id': model.id,
            'partner_field_name': 'id',
        })
        with self.assertRaises(Exception):
            self.env['comm.log.rule'].create({
                'model_id': model.id,
                'partner_field_name': 'id',
            })

    def test_invalid_partner_field_raises(self):
        """A non-existent partner_field_name raises ValidationError."""
        model = self.env['ir.model']._get('res.partner')
        with self.assertRaises(ValidationError):
            self.env['comm.log.rule'].create({
                'model_id': model.id,
                'partner_field_name': 'nonexistent_field',
            })

    def test_valid_partner_field_passes(self):
        """An existing field passes validation."""
        model = self.env['ir.model']._get('res.partner')
        rule = self.env['comm.log.rule'].create({
            'model_id': model.id,
            'partner_field_name': 'email',
        })
        rule._check_partner_field()

    def test_custom_model_partner_field(self):
        """Rule works for crm.lead if the module is installed."""
        if 'crm.lead' not in self.env:
            self.skipTest('crm module not installed')
        model = self.env['ir.model'].search([
            ('model', '=', 'crm.lead'),
        ], limit=1)
        rule = self.env['comm.log.rule'].create({
            'model_id': model.id,
            'partner_field_name': 'partner_id',
        })
        rule._check_partner_field()
