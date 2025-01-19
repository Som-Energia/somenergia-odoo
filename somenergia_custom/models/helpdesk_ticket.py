# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    def button_start_work(self):
        internal_project_ids = self.env['project.project'].get_internal_projects()
        timesheets_to_avoid_timer_ids = self.env['account.analytic.line'].search([
            '|',
            ('som_is_cumulative', '=', True),
            ('project_id', 'in', internal_project_ids.ids),
        ])
        result = super().button_start_work()
        result["context"].update({"resuming_lines": timesheets_to_avoid_timer_ids.ids})
        return result
