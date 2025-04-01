# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    @api.depends('som_message_ids')
    def _compute_som_last_message(self):
        for record in self:
            if record.som_message_ids:
                last_message_id = record.som_message_ids.sorted('date', reverse=True)[:1]
                record.som_last_message_date = last_message_id.date
                if last_message_id.create_uid.id not in record.team_id.user_ids.ids:
                    record.kanban_state = 'blocked'

    som_message_ids = fields.One2many(
        string="Messages",
        comodel_name="mail.message",
        inverse_name="som_ticket_id",
    )

    som_last_message_date = fields.Datetime(
        string = "Last message date",
        compute='_compute_som_last_message',
        store=True,
    )

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

    @api.model
    def message_new(self, msg, custom_values=None):
        ticket_id = super().message_new(msg, custom_values=custom_values)
        # assign default project
        if ticket_id.team_id and ticket_id.team_id.default_project_id:
            ticket_id.project_id = ticket_id.team_id.default_project_id
        return ticket_id
