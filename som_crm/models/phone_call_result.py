# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PhoneCallResult(models.Model):
    _name = 'phone.call.result'
    _description = 'Phone Call Result'
    _order = 'sequence, name'

    name = fields.Char(string='Result Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    sequence = fields.Integer(string='Sequence', default=10, help="Used to order results")
    active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color', help="Color for display purposes")

    # Additional fields for categorization
    result_type = fields.Selection([
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ], string='Result Type', default='neutral', help="Categorize the result type")

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Phone call result name must be unique!'),
    ]



class MailActivity(models.Model):
    _inherit = 'mail.activity'

    phone_call_result_id = fields.Many2one(
        'phone.call.result',
        string='Phone Call Result',
        help="Result of the phone call activity"
    )