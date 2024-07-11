# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, tools, _
from datetime import datetime, timedelta
from odoo.addons.somenergia_custom.pydantic.pydantic_models import WorkRegister
from pydantic import ValidationError
import traceback

_logger = logging.getLogger(__name__)


class SomWorkedWeek(models.Model):
    _name = "som.worked.week"
    _inherit = ["som.common.project", "mail.thread", "mail.activity.mixin"]
    _description = "Som Worked Week"

    @api.depends('som_timesheet_ids', 'som_timesheet_ids.unit_amount')
    def _compute_totals(self):
        for record in self:

            record.som_total_worked_hours = abs(sum(record.som_timesheet_ids.filtered(
                lambda x: x.som_is_cumulative
            ).mapped("unit_amount")))

            record.som_total_assigned_hours = round(sum(record.som_timesheet_ids.filtered(
                lambda x: not x.som_is_cumulative
            ).mapped("unit_amount")), 2)

            som_total_unassigned_hours = round((
                    record.som_total_worked_hours - record.som_total_assigned_hours
            ), 2)

            record.som_total_unassigned_hours = \
                0 if abs(som_total_unassigned_hours) == 0.01 else som_total_unassigned_hours

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

    def get_incomplete_worked_weeks(self):
        reference_day = datetime.now() - timedelta(days=datetime.now().weekday() + 1)
        domain = [
            "&",
            "|",
            "&",
            ("som_total_assigned_hours", "=", 0),
            ("som_total_worked_hours", "!=", 0),
            "&",
            "&",
            ("som_total_assigned_hours", "!=", 0),
            ("som_total_unassigned_hours", "!=", 0),
            ("som_total_worked_hours", "!=", 0),
            ("som_cw_date_rel", "<", fields.Date.to_string(reference_day)),
        ]
        worked_week_ids = self.env['som.worked.week'].search(domain)
        return worked_week_ids

    @api.model
    def send_mail_worked_weeks_reminder(self):
        incomplete_worked_week_ids = self.get_incomplete_worked_weeks()
        employee_ids = incomplete_worked_week_ids.mapped('som_employee_id')

        somadmin_user_id = self.env.ref('base.somadmin')
        for employee_id in employee_ids:
            try:
                mail_html = _("""
                        <t t-set="url" t-value="'www.odoo.com'"/>
                        <div style="margin: 0px; padding: 0px;">
                            <p style="margin: 0px; padding: 0px; font-size: 13px;">
                                Hello, %s
                                <br/><br/>
                                You have past worked weeks incomplete. Please check it and fix it ASAP to have everything right.
                                <br/><br/>
                                <a t-att-href="object.signup_url" style="background-color:#875A7B; padding:8px 16px 8px 16px; text-decoration:none; color:#fff; border-radius:5px" href="https://odoo.somenergia.coop/web#action=419&model=som.worked.week&view_type=list&cids=1&menu_id=207" target="_blank" class="btn btn-primary">See worked weeks</a>
                                <br/><br/>
                                Thanks,
                            </p>
                        </div>
                    """) % (
                    employee_id.display_name,
                )

                mail_values = {
                    'author_id': somadmin_user_id.partner_id.id,
                    'body_html': mail_html,
                    'subject': _('Odoo Som - Worked weeks reminder %s') % datetime.now().strftime('%d/%m/%Y'),
                    'email_from': somadmin_user_id.email_formatted or somadmin_user_id.company_id.catchall or somadmin_user_id.company_id.email,
                    'email_to': employee_id.user_id.email_formatted,
                    'auto_delete': False,
                }

                mail = self.env['mail.mail'].sudo().create(mail_values)
                mail.send()

            except Exception as e:
                _logger.exception("Worked weeks reminder - Unable to send email.")

    def _exception(self, e):
        error_msg = str(e)
        res = {
            "error": error_msg,
        }
        _logger.exception(str(res))
        return res

    @api.model
    def create_worked_week_register(self, data):
        try:
            try:
                obj_wr = WorkRegister.model_validate(data)
            except ValidationError as e:
                return self._exception(e)
            ww_id = self.env['som.worked.week'].search([('id', '=', obj_wr.worked_week_id)])
            if not ww_id:
                return self._exception('The worked week does not exist')
            area_project_id = self.env['project.project'].search([('id', '=', obj_wr.area_project_id)])
            if not area_project_id:
                return self._exception('The area project does not exist')
            if obj_wr.additional_project_id:
                additional_project_id = self.env['project.project'].search([('id', '=', obj_wr.additional_project_id)])
                if not additional_project_id:
                    return self._exception('The additional project does not exist')

            ww_date = ww_id.som_week_id.som_cw_date
            dic_create = {
                "date": fields.Date.to_string(ww_date),
                "som_worked_week_id": ww_id.id,
                "som_week_id": ww_id.som_week_id.id,
                "som_is_cumulative": False,
                "employee_id": ww_id.som_employee_id.id,
                "project_id": obj_wr.area_project_id,
                "name": obj_wr.description,
                "unit_amount": obj_wr.hours,
            }
            if obj_wr.additional_project_id:
                dic_create['som_additional_project_id'] = obj_wr.additional_project_id
            timesheet_id = self.env['account.analytic.line'].create(dic_create)
            return {'timesheet_id': timesheet_id.ids}
        except ValidationError as e:
            return self._exception(traceback.format_exc())
