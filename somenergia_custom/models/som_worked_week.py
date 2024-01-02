# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class SomWorkedWeek(models.Model):
    _name = "som.worked.week"
    _inherit = ["mail.thread", "mail.activity.mixin"]
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

            record.som_total_unassigned_hours = round((
                    record.som_total_worked_hours - record.som_total_assigned_hours
            ), 2)

    def _compute_project_area_domain_ids(self):
        tag_area_id = self.env.ref("somenergia_custom.som_project_tag_area")
        for record in self:
            domain = [("tag_ids", "in", tag_area_id.ids)]
            project_ids = self.env['project.project'].search(domain)
            record.som_project_area_domain_ids = project_ids

    som_week_id = fields.Many2one(
        comodel_name="som.calendar.week",
        string="Week",
        required=True,
    )

    name = fields.Char(
        string="Name",
        related="som_week_id.name",
        store=True,
    )

    som_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        required=True,
    )

    som_timesheet_ids = fields.One2many(
        string="Assignments",
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

    som_project_area_domain_ids = fields.Many2many(
        "project.project",
        string="Projects area domain",
        compute="_compute_project_area_domain_ids",
        store=False,
    )

    # related field from som.calendar.week
    # -----
    som_cw_date_rel = fields.Datetime(
        string="Week Date From",
        related="som_week_id.som_cw_date",
        store=True,
    )

    som_cw_date_end_rel = fields.Datetime(
        string="Week Date End",
        related="som_week_id.som_cw_date_end",
        store=True,
    )

    som_cw_week_number_rel = fields.Integer(
        string="Week Number",
        related="som_week_id.som_cw_week_number",
        store=True,
    )

    som_cw_week_year_rel = fields.Integer(
        string="Week Year Relative",
        related="som_week_id.som_cw_week_year",
        store=True,
    )

    som_cw_year_rel = fields.Integer(
        string="Week Year",
        related="som_week_id.som_cw_week_year",
        store=True,
    )

    # -----
