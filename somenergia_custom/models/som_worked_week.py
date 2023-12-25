# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class SomWorkedWeek(models.Model):
    _name = "som.worked.week"
    _description = "Som Worked Week"

    @api.depends('som_timesheet_ids', 'som_timesheet_ids.unit_amount')
    def _compute_totals(self):
        for record in self:

            record.som_total_worked_hours = abs(sum(record.som_timesheet_ids.filtered(
                lambda x: x.som_is_cumulative
            ).mapped("unit_amount")))

            record.som_total_assigned_hours = sum(record.som_timesheet_ids.filtered(
                lambda x: not x.som_is_cumulative
            ).mapped("unit_amount"))

            record.som_total_unassigned_hours = (
                    record.som_total_worked_hours - record.som_total_assigned_hours
            )

    som_week_id = fields.Many2one(
        comodel_name="som.calendar.week",
        string="Week",
        required=True,
    )

    som_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        required=True,
    )

    som_timesheet_ids = fields.One2many(
        string="Timesheets",
        comodel_name="account.analytic.line",
        inverse_name="som_worked_week_id",
    )

    som_total_worked_hours = fields.Float(
        'Total worked hours',
        compute='_compute_totals',
        store=True,
    )

    som_total_unassigned_hours = fields.Float(
        'Total unassigned hours',
        compute='_compute_totals',
        store=True,
    )

    som_total_assigned_hours = fields.Float(
        'Total assigned hours',
        compute='_compute_totals',
        store=True,
    )
