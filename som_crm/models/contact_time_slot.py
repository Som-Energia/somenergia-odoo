# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ContactTimeSlot(models.Model):
    _name = 'contact.time.slot'
    _description = 'Contact Time Slot'
    _order = 'sequence, name'

    name = fields.Char('Nom', required=True)
    sequence = fields.Integer('Seqüència', default=10)
    active = fields.Boolean('Actiu', default=True)
    color = fields.Integer("Color")
