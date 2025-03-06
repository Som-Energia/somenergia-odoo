# -*- coding: utf-8 -*-
import logging
import pytz
from odoo import models, fields, api, exceptions, _
from datetime import datetime
from datetime import timedelta
from pytz import timezone, utc

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def _compute_som_edition_allowed(self):
        for record in self:
            allowed = True
            if self.env.company.som_amend_attendance_restrictive:
                days_to = self.env.company.som_amend_attendance_days_to
                date_to = fields.Date.to_date(fields.Date.today() - timedelta(days=days_to))
                allowed = (date_to <= record.check_in.date() <= fields.Date.today())
            record.som_edition_allowed = allowed

    som_comments = fields.Text(
        string="Comments"
    )

    som_edition_allowed = fields.Boolean(
        string='Edition allowed',
        compute='_compute_som_edition_allowed',
        store=False,
    )

    def _get_data_time(self, float_hours):
        time_aux = timedelta(hours=abs(float_hours))
        seconds = time_aux.seconds
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return h, m, s

    def get_attendance_hour_limit(self, hour_limit):
        self.ensure_one()
        check_in = self.check_in
        # hour_limit = p_hour_limit or self.employee_id.company_id.attendance_maximum_hours_per_day
        h, m, s = self._get_data_time(hour_limit)
        limit = datetime(check_in.year, check_in.month, check_in.day, h, m, s)
        return limit

    def needs_autoclose(self):
        self.ensure_one()
        check_out_limit = self.get_attendance_hour_limit(self.employee_id.company_id.attendance_maximum_hours_per_day)
        if self.check_in < check_out_limit <= fields.Datetime.now():
            return True
        return False

    def get_checkout_time(self):
        self.ensure_one()
        check_out_aux = self.get_attendance_hour_limit(self.employee_id.company_id.attendance_maximum_hours_per_day)
        return self._get_local_tz_datetime(check_out_aux)

    def _get_local_tz_datetime(self, datetime_aux):
        local_tz = timezone('Europe/Madrid')
        local_dt = local_tz.localize(datetime_aux, is_dst=None)
        dt_time_utc = local_dt.astimezone(utc)
        dt_str = dt_time_utc.strftime("%m/%d/%Y %H:%M:%S")
        dt_time = datetime.strptime(dt_str, "%m/%d/%Y %H:%M:%S")
        return dt_time

    def get_hours_today_without_me(self):
        self.ensure_one()
        att_ids = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('id', '!=', self.id),
            ('check_in', '!=', False),
            ('check_out', '!=', False),
        ])
        worked_hours = 0
        for att_id in att_ids.filtered(lambda x: x.check_in.date() == self.check_in.date()):
            delta = att_id.check_out - att_id.check_in
            worked_hours += delta.total_seconds() / 3600.0
        return worked_hours

    def get_max_hours_today(self):
        self.ensure_one()
        th = self.env['hr.attendance.theoretical.time.report']._theoretical_hours(
            self.employee_id.sudo(), self.check_in.date() or datetime.today()
        )
        max_ov_hours = self.employee_id.sudo().som_current_calendar_id.som_max_overtime_per_day
        return th + max_ov_hours

    def get_max_checkout(self):
        self.ensure_one()
        if not self.check_in:
            return False
        max_hours_today = self.get_max_hours_today()
        hours_today_no_me = self.get_hours_today_without_me()

        time_left = max_hours_today - hours_today_no_me
        h, m, s = self._get_data_time(time_left)
        time_aux = timedelta(hours=h, minutes=m, seconds=s)

        max_check_out = self.check_in + time_aux
        return max_check_out

    def autoclose_attendance(self, reason):
        try:
            self.ensure_one()
            vals = {"check_out": self.check_in}
            if reason:
                vals["attendance_reason_ids"] = [(4, reason.id)]
            self.write(vals)
            self.send_mail_autoclose()
        except Exception as e:
            _logger.info("Exception 'autoclose_attendance': %s " % e)
            return False

    @api.model
    def som_check_attendance_reason(self):
        att_reason_id = self.env.ref('hr_attendance_autoclose.hr_attendance_reason_check_out')
        att_ids = self.search([
            ("attendance_reason_ids", "ilike", att_reason_id.name)
        ])
        att_remove_reason_ids = att_ids.filtered(
            lambda x: x.check_in != x.check_out and x.check_out != x.get_checkout_time()
        )
        att_remove_reason_ids.write({
            'attendance_reason_ids': [(3, att_reason_id.id)]
        })

    @api.model
    def check_for_incomplete_attendances(self):
        self.som_check_attendance_reason()
        super().check_for_incomplete_attendances()

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

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_overtime(self):
        if self.env.company.som_restrictive_overtime:
            for att_id in self.filtered(lambda x: x.check_in and x.check_out):
                max_check_out = att_id.get_max_checkout()
                if att_id.check_out > max_check_out:
                    user_tz = att_id.employee_id.user_id.sudo().tz
                    max_check_out_tz = max_check_out.astimezone(pytz.timezone(user_tz))
                    str_max_check_out_tz = max_check_out_tz.strftime('%d/%m/%Y %H:%M:%S')
                    raise exceptions.ValidationError(
                        _("L'hora màxima per tancar l'assistència és %(max_check_out)s " % {
                              'max_check_out': str_max_check_out_tz,
                          })
                    )

    def write(self, vals):
        if (self.env.company.som_restrictive_overtime and
                vals.get('check_out') and self.env.context.get('som_from_attendance_action_change')):
            for att_id in self: # we do it but in theory just one record expected
                origin_check_out = vals.get('check_out')
                max_check_out = att_id.get_max_checkout()
                if origin_check_out > max_check_out:
                    vals['check_out'] = max_check_out
                    vals['som_comments'] = '-'
                    self.send_mail_attendance_reminder(att_id, origin_check_out, max_check_out)
        return super().write(vals)

    @api.model
    def send_mail_attendance_reminder(self, att_id, origin_checkout, new_checkout):
        somadmin_user_id = self.env.ref('base.somadmin')
        user_tz = att_id.employee_id.user_id.sudo().tz
        str_day = new_checkout.astimezone(pytz.timezone(user_tz)).strftime('%d/%m/%Y')
        float_hours_diff = (origin_checkout - new_checkout).total_seconds() / 3600
        h, m, s = self._get_data_time(float_hours_diff)
        str_mail_body = "%s -> %s [- %s:%s:%s]" % (
            origin_checkout.astimezone(pytz.timezone(user_tz)).strftime('%d/%m/%Y %H:%M'),
            new_checkout.astimezone(pytz.timezone(user_tz)).strftime('%d/%m/%Y %H:%M'),
            h, m, s,
        )
        str_subject = _("Recordatori dia: %s [%s]" % (str_day, str(att_id.id)))
        try:
            mail_html = _("""
                                <div style="margin: 0px; padding: 0px;">
                                    <p style="margin: 0px; padding: 0px; font-size: 13px;">
                                        Hola,
                                        <br/><br/>
                                        %s
                                        <br/><br/>
                                        %s
                                        <br/><br/>
                                        Salut!
                                    </p>
                                </div>
                            """) % (
                str_subject,
                str_mail_body,
            )

            mail_values = {
                'author_id': somadmin_user_id.partner_id.id,
                'body_html': mail_html,
                'subject': str_subject,
                'email_from':
                    somadmin_user_id.email_formatted or somadmin_user_id.company_id.catchall or
                    somadmin_user_id.company_id.email,
                'email_to': att_id.employee_id.user_id.email_formatted,
                'auto_delete': False,
            }

            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()

        except Exception as e:
            _logger.exception("send_mail_attendance_reminder - unable to send email.")

    @api.constrains('check_in', 'check_out')
    def _check_validity_hour_limits(self):
        hour_limit_start = self.env.company.som_attendance_limit_checkin
        hour_limit_end = self.env.company.som_attendance_limit_checkout
        for att_id in self:
            checkin_limit = att_id.get_attendance_hour_limit(hour_limit_start)
            checkin_limit_tz = self._get_local_tz_datetime(checkin_limit)
            checkout_limit = att_id.get_attendance_hour_limit(hour_limit_end)
            checkout_limit_tz = self._get_local_tz_datetime(checkout_limit)
            if att_id.check_in and att_id.check_in < checkin_limit_tz:
                raise exceptions.ValidationError(
                    _("No es pot obrir l'assitència abans de les %(limit)s" % {
                          'limit': checkin_limit.strftime('%d/%m/%Y %H:%M'),
                      })
                )
            if att_id.check_out and att_id.check_out > checkout_limit_tz:
                raise exceptions.ValidationError(
                    _("No es pot tancar l'assitència després de les %(limit)s" % {
                          'limit': checkout_limit.strftime('%d/%m/%Y %H:%M'),
                      })
                )

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity_leaves(self):
        feature_flag_date_from = datetime.today()
        try:
            str_date = self.env["ir.config_parameter"].sudo().get_param("som_ff_date_from_overlapping_attendance")
            feature_flag_date_from = datetime.strptime(str_date, '%Y-%m-%d')
        except Exception:
            pass
        leave_from_id = self._context.get('leave_from_id', False)
        for att_id in self.filtered(lambda x: x.check_in > feature_flag_date_from):
            domain_aux = [
                ("employee_id", "=", att_id.employee_id.id),
                ("state", "in", ["confirm", "validate"]),
            ]
            if leave_from_id:
                domain_aux.append(('id', '=', leave_from_id.id))
            emp_leave_ids = self.env["hr.leave"].search(domain_aux).filtered(
                lambda x: (
                        (
                                (x.request_unit_half or x.request_unit_hours)
                                and
                                (
                                        (att_id.check_in and x.date_from <= att_id.check_in < x.date_to)
                                        or
                                        (att_id.check_out and x.date_from < att_id.check_out < x.date_to)
                                        or
                                        (att_id.check_in and att_id.check_out and att_id.check_in < x.date_from
                                         and x.date_to < att_id.check_out)
                                )
                        )
                        or
                        (
                                (not x.request_unit_half and not x.request_unit_hours)
                                and
                                (
                                        (att_id.check_in
                                         and x.request_date_from <= att_id.check_in.date() <= x.request_date_to)
                                        or
                                        (att_id.check_out
                                         and x.request_date_from <= att_id.check_out.date() <= x.request_date_to)
                                        or
                                        (att_id.check_in and att_id.check_out
                                         and att_id.check_in.date() <= x.request_date_from
                                         and x.request_date_to < att_id.check_out.date())
                                )
                        )
                )
            )
            if emp_leave_ids:
                if leave_from_id:
                    raise exceptions.ValidationError(
                        _("No es pot registrar l'absència per a %(empl_name)s, "
                          "l'empledada té assitències en aquest període de temps:\n%(att_name)s" % {
                              'empl_name': att_id.employee_id.name,
                              'att_name': att_id.name_get(),
                          })
                    )
                else:
                    raise exceptions.ValidationError(
                        _("No es pot registrar l'assitència per a %(empl_name)s, "
                          "l'empledada té absències en aquest període de temps:\n%(abs_name)s" % {
                              'empl_name': att_id.employee_id.name,
                              'abs_name': emp_leave_ids[0].name_get(),
                          })
                    )
