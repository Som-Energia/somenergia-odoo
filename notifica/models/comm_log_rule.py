# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class CommLogRule(models.Model):
    _name = 'comm.log.rule'
    _description = 'Communication Log Rule'
    _order = 'model_id ASC'
    _rec_name = 'model_id'

    model_id = fields.Many2one(
        'ir.model',
        string='Source Model',
        required=True,
        ondelete='cascade',
        help='Document model that triggers automatic log capture.',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    partner_field_name = fields.Char(
        string='Partner Field',
        required=True,
        default='partner_id',
        help="Technical field name holding the partner relation "
             "(e.g. 'partner_id', 'customer_id').",
    )
    include_child_contacts = fields.Boolean(
        string='Include Child Contacts',
        default=False,
        help="When enabled, communications are also logged for child "
             "contacts of the main partner.",
    )
    description = fields.Char(string='Description')

    _sql_constraints = [
        (
            'unique_model',
            'UNIQUE(model_id)',
            'A rule already exists for this model.',
        ),
    ]

    @api.constrains('partner_field_name', 'model_id')
    def _check_partner_field(self):
        for record in self:
            if not record.model_id or not record.partner_field_name:
                continue
            model_obj = self.env.get(record.model_id.model)
            if model_obj is None:
                raise ValidationError(_(
                    'Model "%s" not found in the current environment.'
                ) % record.model_id.model)
            if record.partner_field_name not in model_obj._fields:
                raise ValidationError(_(
                    'Field "%s" does not exist on model "%s".'
                ) % (record.partner_field_name, record.model_id.name))
