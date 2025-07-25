# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError
from odoo.tools import float_round


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"


    def _compute_som_is_absent_regardless_state(self):
        # Used SUPERUSER_ID to forcefully get status of other user's leave, to bypass record rule
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('date_from', '<=', fields.Datetime.now()),
            ('date_to', '>=', fields.Datetime.now()),
        ])
        leave_data = {leave.employee_id.id: leave.state for leave in holidays}

        for employee in self:
            employee.som_is_absent_regardless_state = leave_data.get(employee.id, False)

    def _compute_is_present(self):
        for record in self:
            record.is_present = not record.som_is_absent_regardless_state

    def _search_present_employee(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        employee_ids = self.env['hr.employee'].search([('som_is_absent_regardless_state', '=', False)])
        operator = ['in', 'not in'][(operator == '=') != value]
        return [('id', operator, employee_ids.ids)]

    def _search_absent_regardless_state(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        # This search is only used for the 'Absent today not validated' filter however
        # this only returns employees that are absent right now.
        today_date = datetime.datetime.utcnow().date()
        today_start = fields.Datetime.to_string(today_date)
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', '!=', False),
            ('date_from', '<=', today_end),
            ('date_to', '>=', today_start),
        ])
        operator = ['in', 'not in'][(operator == '=') != value]
        return [('id', operator, holidays.mapped('employee_id').ids)]

    som_current_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
    )

    som_is_absent_regardless_state = fields.Boolean(
        string='Absent today regardless of state',
        compute='_compute_som_is_absent_regardless_state',
        store=False,
        search='_search_absent_regardless_state'
    )

    is_present = fields.Boolean(
        string='Present today',
        compute='_compute_is_present',
        store=False,
        search='_search_present_employee'
    )

    som_recruitment_date = fields.Date(
        string="Recruitment date",
    )

    som_appraisal_ref_date = fields.Date(
        string="Feedback ref date",
    )

    som_excluded_from_tel_assistance = fields.Boolean(
        string='Excluded from telephone assistance',
    )


class HrEmployee(models.Model):
    _inherit = "hr.employee"


    @api.depends('calendar_ids', 'calendar_ids.date_start', 'calendar_ids.date_end')
    def _compute_current_calendar(self):
        for record in self:
            calendar_id = record.calendar_ids.filtered(
                lambda x: (x.date_start and x.date_start <= fields.Date.today() and
                           (not x.date_end or (x.date_end and x.date_end >= fields.Date.today()))) or
                          (not x.date_start and not x.date_end)
            )
            record.som_current_calendar_id = calendar_id[0].calendar_id.id if calendar_id else False

    som_current_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Current calendar",
        compute='_compute_current_calendar',
        store=True,
        compute_sudo=True,
    )

    @api.depends('overtime_ids.duration', 'attendance_ids')
    def _compute_total_overtime(self):
        for employee in self:
            if employee.company_id.hr_attendance_overtime:
                overtime_this_year_ids = employee.overtime_ids.filtered(
                    lambda x: x.date.year == datetime.date.today().year
                )
                employee.total_overtime = float_round(sum(overtime_this_year_ids.mapped('duration')), 2)
            else:
                employee.total_overtime = 0

    @api.model
    def _check_no_current_calendar_employees(self):
        emp_ids = self.env['hr.employee'].search([('som_current_calendar_id', '=', False)])
        emp_ids._compute_current_calendar()

    def _attendance_action_change(self):
        attendance = super(
            HrEmployee, self.with_context(som_from_attendance_action_change=True)
        )._attendance_action_change()
        # attendance = super()._attendance_action_change()
        return attendance

    @api.model
    def get_available_worker_emails(self, department):
        """
        This function returns a list with the emails of available employees
        It's used by 'Info dispatcher'
        """
        empl_ids = self.env['hr.employee'].search([
            ('department_ids', 'ilike', department),
            ('is_present', '=', True),
            ('som_excluded_from_tel_assistance', '=', False),
        ])
        res = [empl_id.user_id.email for empl_id in empl_ids]
        return res


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"


    department_ids = fields.Many2many(
        readonly=True,
    )

    som_current_calendar_id = fields.Many2one(
        readonly=True,
    )

    som_recruitment_date = fields.Date(
        readonly=True,
    )
