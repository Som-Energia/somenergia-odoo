
from odoo import models, fields, _
import logging
import datetime
from odoo.addons.resource.models.resource import float_to_time
from pytz import timezone, UTC

_logger = logging.getLogger(__name__)


class HrAttendanceAbsence(models.TransientModel):
    _name = 'hr.attendance.absence'

    absence_message = fields.Text("Missatge", help="Missatge que s'enviara al grup de laboral",
                                  default="Avui no em trobo amb forces per assistir a la feina.")

    def run(self):
        user = self.env.user
        employee_id = self.env['hr.employee'].search(
            [('user_id', '=', user.id)])
        resource_calendar_id = employee_id.resource_id.calendar_id
        target_ranges = []
        for r in resource_calendar_id.attendance_ids:
            if (r.date_from <= datetime.datetime.today().date()
                and (not r.date_to or r.date_to >= datetime.datetime.today().date())
                    and datetime.datetime.today().date().weekday() == int(r.dayofweek)):
                target_ranges.append(r)

        min_hour = 2.0
        max_hour = 22.0
        for r in target_ranges:
            if len(target_ranges) == 1:
                if r.hour_from > min_hour:
                    min_hour = r.hour_from
                if r.hour_to < max_hour:
                    max_hour = r.hour_to
            else:  # morning & afternoon
                if r.day_period == 'morning':
                    if r.hour_from > min_hour:
                        min_hour = r.hour_from
                if r.day_period == 'afternoon':
                    if r.hour_to < max_hour:
                        max_hour = r.hour_to

        hour_from = float_to_time(min_hour)
        hour_to = float_to_time(max_hour)

        # Create Leave
        today = datetime.datetime.today().strftime("%Y-%m-%d")
        # lt_avuinovinc = self.env['ir.model.data'].get_object_reference('somenergia_custom','leave_avui_no_vinc')[1]
        lt_avuinovinc = self.env.ref("somenergia_custom.leave_avui_no_vinc")

        leave_values = {
            'holiday_type': 'employee',
            'holiday_status_id': lt_avuinovinc.id,
            'request_date_from': today,
            'request_date_to': today,
            'date_from': timezone(user.tz).localize(datetime.datetime.combine(datetime.datetime.today().date(), hour_from)).astimezone(UTC).replace(tzinfo=None),
            'date_to': timezone(user.tz).localize(datetime.datetime.combine(datetime.datetime.today().date(), hour_to)).astimezone(UTC).replace(tzinfo=None),
            'request_date_from_period': 'am',
            'name': self.absence_message,
            'employee_id': employee_id.id,
            'number_of_days': 1,
            'message_attachment_count': 0,
        }

        self.env['hr.leave'].create(leave_values)

        # Send Email
        mail_html = "<p>{} avui no vindrá. Ha escrit el següent missatge: </p><p>{}</p>".format(
            user.display_name,
            self.absence_message)

        mail_values = {
            'body_html': mail_html,
            'subject':  'Avui no vinc {}'.format(user.display_name),
            'email_from': user.partner_id.email or user.company_id.catchall or user.company_id.email,
            'email_to': self.env["ir.config_parameter"].sudo().get_param("som_mail_avui_no_vinc"),
            'auto_delete': False,
        }
        try:
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
        except Exception:
            _logger.exception("Unable to send email when report a 'Avui No vinc' leave")

        return True
