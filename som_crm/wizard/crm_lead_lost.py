
# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CrmLeadLost(models.TransientModel):
    _inherit = 'crm.lead.lost'

    lost_reason_id = fields.Many2one(
        'crm.lost.reason',
        string='Lost Reason',
        required=True
    )

    @api.constrains('lost_reason_id')
    def _check_lost_reason_id(self):
        for record in self:
            if not record.lost_reason_id:
                raise ValidationError("Lost reason is required.")