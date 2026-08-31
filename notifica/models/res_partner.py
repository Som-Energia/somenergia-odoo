# -*- coding: utf-8 -*-
from odoo import api, models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    comm_log_ids = fields.One2many(
        'comm.log', 'partner_id',
        string='Communications',
    )
    comm_log_count = fields.Integer(
        string='Communication Count',
        compute='_compute_comm_log_count',
        store=True,
    )

    @api.depends('comm_log_ids')
    def _compute_comm_log_count(self):
        for partner in self:
            partner.comm_log_count = len(partner.comm_log_ids)
