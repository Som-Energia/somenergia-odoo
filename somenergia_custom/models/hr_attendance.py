# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from datetime import datetime
from datetime import timedelta
from pytz import timezone, utc


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    som_comments = fields.Text(
        string="Comments"
    )

    def _get_data_time(self, float_hours):
        time_aux = timedelta(hours=abs(float_hours))
        seconds = time_aux.seconds
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return h, m, s

    def get_attendance_hour_limit(self):
        self.ensure_one()
        check_in = self.check_in
        hour_limit = self.employee_id.company_id.attendance_maximum_hours_per_day
        h, m, s = self._get_data_time(hour_limit)
        check_out_limit = datetime(check_in.year, check_in.month, check_in.day, h, m, s)
        return check_out_limit

    def needs_autoclose(self):
        self.ensure_one()
        check_out_limit = self.get_attendance_hour_limit()
        if self.check_in < check_out_limit <= fields.Datetime.now():
            return True
        return False

    def autoclose_attendance(self, reason):
        self.ensure_one()
        check_out_aux = self.get_attendance_hour_limit()
        localtz = timezone('Europe/Madrid')
        local_dt = localtz.localize(check_out_aux, is_dst=None)
        checkout_time_utc = local_dt.astimezone(utc)
        checkout_str = checkout_time_utc.strftime("%m/%d/%Y %H:%M:%S")
        checkout_time = datetime.strptime(checkout_str, "%m/%d/%Y %H:%M:%S")
        vals = {"check_out": checkout_time}
        if reason:
            vals["attendance_reason_ids"] = [(4, reason.id)]
        self.write(vals)
