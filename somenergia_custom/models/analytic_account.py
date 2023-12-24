# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    som_week_id = fields.Many2one(
        comodel_name="som.calendar.week",
        string="Week"
    )

    @api.onchange('som_week_id')
    def on_week(self):
        if self.som_week_id:
            self.date = self.som_week_id.som_cw_date.date()

