# -*- coding: utf-8 -*-
from odoo import exceptions, fields, models, api


class MailMessage(models.Model):
    _inherit = 'mail.message'

    som_ticket_id = fields.Many2one(
        comodel_name="helpdesk.ticket",
        string="Helpdesk ticket",
        ondelete="cascade",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('model') == 'helpdesk.ticket' and vals.get('res_id'):
                vals['som_ticket_id'] = vals.get('res_id')
        message_ids = super().create(vals_list)
        return message_ids
