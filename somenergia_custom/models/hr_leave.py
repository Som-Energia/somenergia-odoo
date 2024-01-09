# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY
from odoo.addons.hr_holidays.models.hr_leave import DummyAttendance
from datetime import datetime
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

    def _get_resource_calendar_attendance_target(self, date):
        employee_id = self.env['hr.employee'].search(
            [('user_id', '=', self.env.user.id)])
        if self.employee_ids:
            employee_id = self.employee_ids[0]
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
    def get_leaves(self, start_date, end_date):
        """
        This function returns leaves from start_date to end_date in the following
        format: {'worker': email, 'start_time': '2021-12-30','end_time': '2021-12-31'}
        """
        res = []
        resources_calendar_leaves_model = self.env["resource.calendar.leaves"]
        resource_resource_model = self.env["resource.resource"]
        search_params = [
            ('date_to', '>=', start_date),
            ('date_from', '<=', end_date),
            ('holiday_id', '!=', False)
        ]
        leaves = resources_calendar_leaves_model.search(search_params)

        for leave_id in leaves.ids:
            leave_data = resources_calendar_leaves_model.browse(leave_id)
            worker = leave_data.resource_id.user_id.email
            res.append({
                'worker': worker,
                'start_time': leave_data.date_from,
                'end_time': leave_data.date_to
            })

        return res
