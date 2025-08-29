# -*- coding: utf-8 -*-

from odoo import fields, models, api


class Lead(models.Model):
    _inherit = 'crm.lead'

    som_cups = fields.Char(
        string='CUPS',
        required=False,
    )

    som_preferred_contact_time_ids = fields.Many2many(
        'contact.time.slot',
        'lead_contact_time_rel',
        'lead_id',
        'time_slot_id',
        string='Preferred contact time',
    )
