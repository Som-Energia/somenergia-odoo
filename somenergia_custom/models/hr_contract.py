# -*- coding:utf-8 -*-
from odoo import api, models, fields


class HrContract(models.Model):
    _inherit = 'hr.contract'

    kanban_state = fields.Selection(default='done')

    @api.model
    def update_state(self):
        res = super().update_state()
        return res
