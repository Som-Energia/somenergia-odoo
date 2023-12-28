# -*- coding: utf-8 -*-

from logging import getLogger
from odoo import api, fields, models, _
from odoo.modules.module import get_module_resource

_logger = getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    name = fields.Char(
        default="/"
    )

    som_worked_week_id = fields.Many2one(
        comodel_name="som.worked.week",
        string="Worked week",
    )

    som_week_id = fields.Many2one(
        comodel_name="som.calendar.week",
        string="Week"
    )

    som_is_cumulative = fields.Boolean(
        string="Is cumulative"
    )

    def unlink(self):
        for record in self:
            if self.som_is_cumulative:
                return False
        return super().unlink()

    @api.onchange('som_week_id')
    def onchange_week(self):
        self.date = (
            self.som_week_id.som_cw_date.date() if self.som_week_id else False
        )

    def _get_cumulative_timesheet_week(self, employee_id, year):
        query_name = "query_get_wh_employee_by_weeek.sql"
        query_file = get_module_resource(
            "somenergia_custom", "query", query_name
        )
        query = open(query_file).read()
        cr = self.env.cr
        result = []
        cr.execute(
            query, (
                employee_id.id, employee_id.id,
                year, year
            )
        )
        result = cr.fetchall()
        return result

    @api.model
    def _do_load_wh_week_timesheets_current_user(self):
        year = fields.Date.today().year
        list_employee = []
        if not self.env.user._is_admin():
            list_employee.append(self.env.user.employee_id.id)
        self._do_load_wh_week_timesheets(year, list_employee)

    @api.model
    def _do_load_wh_week_timesheets(self, year, list_employee=[]):
        _logger.info('START - _do_load_wh_week_timesheets')
        project_ch_id = self.env.ref(
            'somenergia_custom.som_cumulative_hours_project'
        )

        domain = []
        if list_employee:
            domain = [('id', 'in', list_employee)]

        employee_ids = self.env['hr.employee'].search(domain)
        for employee_id in employee_ids:
            _logger.info("loading employee '[%s] %s'" % (employee_id.id, employee_id.name))
            worked_hours = self._get_cumulative_timesheet_week(employee_id, year)
            for worked_week in worked_hours:
                id_week = worked_week[0]
                week_name = worked_week[1]
                week_date = worked_week[2].date()
                worked_hours = round(worked_week[4], 2)

                worked_week_id = self.env['som.worked.week'].search([
                    ('som_employee_id', '=', employee_id.id),
                    ('som_week_id', '=', id_week),
                ])
                if not worked_week_id:
                    worked_week_id = self.env['som.worked.week'].create({
                        'som_employee_id': employee_id.id,
                        'som_week_id': id_week,
                    })

                timesheet_id = self.env['account.analytic.line'].search([
                    ('employee_id', '=', employee_id.id),
                    ('som_week_id', '=', id_week),
                    ('project_id', '=', project_ch_id.id),
                ])
                if timesheet_id:
                    timesheet_id.unit_amount = worked_hours
                else:
                    timesheet_id = self.env['account.analytic.line'].create({
                        'date': week_date,
                        'som_worked_week_id': worked_week_id.id,
                        'som_week_id': id_week,
                        'som_is_cumulative': True,
                        'employee_id': employee_id.id,
                        'project_id': project_ch_id.id,
                        'name': week_name,
                        'unit_amount': worked_hours,
                    })
            pass
