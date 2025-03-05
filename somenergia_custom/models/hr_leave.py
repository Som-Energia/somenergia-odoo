# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY
from datetime import datetime
from odoo.addons.hr_holidays.models.hr_leave import DummyAttendance
from pytz import timezone, UTC


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    @api.depends('request_date_from')
    def _today_attendance_text(self):
        for leave in self:
            leave.som_today_attendance_text = self._get_current_leave_attendance_text()

    som_today_attendance_text = fields.Char(
        'Jornada teòrica',
        compute='_today_attendance_text',
        store=False
    )

    som_mandatory_description_rel = fields.Boolean(
        string="Mandatory description",
        related="holiday_status_id.som_mandatory_description",
        store=False,
        readonly=True,
    )

    def _get_resource_calendar_attendance_target(self, date):
        employee_id = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.user.id)])
        if self.sudo().employee_ids:
            employee_id = self.sudo().employee_ids[0]
        resource_calendar_id = employee_id.resource_id.calendar_id
        target_ranges = []
        for r in resource_calendar_id.attendance_ids:
            if ((not r.date_from or r.date_from <= date)
                and (not r.date_to or r.date_to >= date)
                    and (date.weekday() == int(r.dayofweek))):
                target_ranges.append(r)
        return target_ranges

    @api.model
    def _get_current_leave_attendance_text(self):
        if not self.date_from:
            return ""
        date = self.date_from.date()
        att_text, morning_att_text, afternoon_att_text = '','',''
        target_ranges = self._get_resource_calendar_attendance_target(date)
        for r in target_ranges:
            if len(target_ranges) == 1:
                att_text = ' {}: de {} a {}'.format(
                    (r.day_period == 'morning' and 'Matí') or 'Tarda',
                    float_to_time(r.hour_from).strftime("%H:%M"),
                    float_to_time(r.hour_to).strftime("%H:%M"),
                )
            else:  # morning & afternoon
                if r.day_period == 'morning':
                    morning_att_text = 'Matí: de {} a {}'.format(
                        float_to_time(r.hour_from).strftime("%H:%M"),
                        float_to_time(r.hour_to).strftime("%H:%M"),
                    )
                if r.day_period == 'afternoon':
                    afternoon_att_text = 'Tarda: de {} a {}'.format(
                        float_to_time(r.hour_from).strftime("%H:%M"),
                        float_to_time(r.hour_to).strftime("%H:%M"),
                    )
                att_text = " {} / {}".format(morning_att_text,afternoon_att_text)

        return att_text

    def _is_in_ranges(self, hour, ranges):
        for range_id in ranges:
            if range_id.hour_from <= hour <= range_id.hour_to:
                return True
        return False

    @api.onchange('request_hour_from', 'request_hour_to')
    def on_change_leave_custom_hours(self):
        if (self.request_hour_from or self.request_hour_to) and self.date_from:
            date = self.date_from.date()
            target_ranges = self._get_resource_calendar_attendance_target(date)
            value_aux, field_name, field_label = "", "", ""
            # self._fields[field_name]._related_string
            if self.request_hour_from and not self._is_in_ranges(float(self.request_hour_from), target_ranges):
                value_aux = self.request_hour_from
                field_name = "request_hour_from"
                field_label = "Des de"
            if self.request_hour_to and not self._is_in_ranges(float(self.request_hour_to), target_ranges):
                value_aux = self.request_hour_to
                field_name = "request_hour_to"
                field_label = "Fins a"
            if value_aux:
                str_hour = dict(
                    self._fields[field_name]._description_selection(self.env))[self[field_name]]
                self[field_name] = False

                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _("'%s' with value '%s' out of time table") % (
                            field_label,
                            str_hour,
                        ),
                    }
                }

    @api.model
    def get_mail_employees_from_departments(self, department_ids):
        # we got a list of mail lists by department
        list_aux = [dep_id.member_ids.mapped("user_id.email") for dep_id in department_ids]
        # we get a unique list with all mails
        list_result = list(set([mail for sublist in list_aux for mail in sublist]))
        return list_result

    @api.model
    def get_leaves(self, start_date, end_date):
        """
        This function returns leaves from start_date to end_date in the following
        format: {'worker': email, 'start_time': '2021-12-30','end_time': '2021-12-31'}
        """
        res = []
        search_params = [
            ('date_to', '>=', start_date),
            ('date_from', '<=', end_date),
        ]
        leave_ids = self.env['hr.leave'].search(search_params)

        for leave_id in leave_ids:
            worker = leave_id.employee_id.user_id.email
            res.append({
                'worker': worker,
                'start_time': leave_id.date_from,
                'end_time': leave_id.date_to
            })

        # get from stress_days with departments
        sd_leave_ids = self.env['hr.leave.stress.day'].search([
            ('start_date', '>=', start_date),
            ('end_date', '<=', end_date),
            ('som_type', '=', 'no_service'),
            ('department_ids', '!=', False),
        ])

        # overlapping stress_day dates with leaves does not matter
        for sd_leave_id in sd_leave_ids:
            list_mails_employees = self.get_mail_employees_from_departments(sd_leave_id.department_ids)
            start_datetime = datetime(
                sd_leave_id.start_date.year, sd_leave_id.start_date.month, sd_leave_id.start_date.day,7, 0, 0
            )
            end_datetime = datetime(
                sd_leave_id.end_date.year, sd_leave_id.end_date.month, sd_leave_id.end_date.day,14, 0, 0
            )
            for mail in list_mails_employees:
                res.append({
                    'worker': mail,
                    'start_time': start_datetime,
                    'end_time': end_datetime,
                })

        return res

    def write(self, vals):
        return super(HolidaysRequest, self.with_context(leave_skip_date_check=True)).write(vals)

    @api.constrains('date_from', 'date_to', 'employee_ids')
    def _check_validity_attendances(self):
        for absence_id in self.sudo():
            domain_aux = [
                ("employee_id", "in", absence_id.employee_ids.ids),
            ]
            att_ids = self.env["hr.attendance"].search(domain_aux)
            att_ids.with_context(leave_from_id=absence_id)._check_validity_leaves()

    @api.constrains('date_from', 'date_to')
    def _check_stress_day(self):
        if self.env.company.som_restrictive_stress_days:
            return super()._check_stress_day()
