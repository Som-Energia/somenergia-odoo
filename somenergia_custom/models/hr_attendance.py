# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, exceptions, _
from datetime import datetime
from datetime import timedelta
from pytz import timezone, utc

_logger = logging.getLogger(__name__)


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
        self.send_mail_autoclose()

    def send_mail_autoclose(self):
        somadmin_user_id = self.env.ref('base.somadmin')
        for record in self:
            employee_id = record.employee_id
            checkout_time = record.check_out
            try:
                mail_html = _("""
                    <t t-set="url" t-value="'www.odoo.com'"/>
                    <div style="margin: 0px; padding: 0px;">
                        <p style="margin: 0px; padding: 0px; font-size: 13px;">
                            Hello, %s 
                            <br/><br/>
                            Your attendance for the day %s has been closed automatically. Please check it and fix it to have your attendance right.
                            <br/><br/>
                            <a t-att-href="object.signup_url" style="background-color:#875A7B; padding:8px 16px 8px 16px; text-decoration:none; color:#fff; border-radius:5px" href="https://odoo.somenergia.coop/web#action=304&amp;model=hr.attendance&amp;view_type=list&amp;cids=1&amp;menu_id=207" target="_blank" class="btn btn-primary">Veure assistències</a>
                            <br/><br/>
                            Thanks,
                        </p>
                    </div>
                """) % (
                    employee_id.display_name,
                    checkout_time.strftime('%d/%m/%Y'),
                )

                mail_values = {
                    'author_id': somadmin_user_id.partner_id.id,
                    'body_html': mail_html,
                    'subject': _('Odoo Som - Attendance closed automatically %s') % checkout_time.strftime('%d/%m/%Y'),
                    'email_from': somadmin_user_id.email_formatted or somadmin_user_id.company_id.catchall or somadmin_user_id.company_id.email,
                    'email_to': employee_id.user_id.email_formatted,
                    'auto_delete': False,
                }

                mail = self.env['mail.mail'].sudo().create(mail_values)
                mail.send()
            except Exception:
                _logger.exception("Attendance autoclose - Unable to send email.")
