# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from pathlib import Path
from logging import getLogger
import datetime
import os

_logger = getLogger(__name__)


class HRAttendanceOvertime(models.Model):
    _inherit = "hr.attendance.overtime"

    def action_view_attendances(self):
        # action_id = self.env.ref('hr_attendance.hr_attendance_action')
        tree_view_id = self.env.ref('hr_attendance.view_attendance_tree')
        date_to = fields.Date.add(self.date, days=1)
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', self.date),
            ('check_out', '<', date_to)
        ]
        action_open_attendances = {
            'name': _('Day attendances %s' % self.date.strftime("%d/%m/%Y")),
            'view_type': 'tree',
            'res_model': 'hr.attendance',
            'domain': domain,
            'view_id': tree_view_id.id,
            'views': [
                (tree_view_id.id, 'tree'),
            ],
            'type': 'ir.actions.act_window',
        }

        return action_open_attendances

    def _get_weekdays_of_year_until_today(self):
        # Get today's date
        # TODO: change for real today when deploy to prod
        today = datetime.date(2024, 9, 17) # datetime.date.today()

        # Start on January 1st of the current year
        start_date = datetime.date(today.year, 1, 1)

        # Calculate the number of days from January 1st until today
        days_until_today = (today - start_date).days + 1  # Adding 1 to include today

        # Generate list of all weekdays (Monday to Friday)
        weekdays = [
            (start_date + datetime.timedelta(days=i)).isoformat()
            for i in range(days_until_today)
            if (start_date + datetime.timedelta(days=i)).weekday() < 5  # 0=Monday, ..., 4=Friday
        ]

        return weekdays

    def _create_overtime_fixing_attendance(self, employee_id, str_day):
        att_reason_id = self.env.ref("hr_attendance_reason.hr_act_reason_1")
        comment = "Ajust dia no treballat"
        att_id = self.env['hr.attendance'].create({
            'employee_id': employee_id.id,
            'check_in': str_day,
            'check_out': str_day,
            'attendance_reason_ids': [(4, att_reason_id.id)],
            'som_comments': comment,
        })
        return att_id


    def _do_fix_compute_overtime(self):
        _logger.info("_do_fix_compute_overtime: start")
        days_of_year_until_today = self._get_weekdays_of_year_until_today()
        str_result = ''
        for emp_id in self.env['hr.employee'].search([('id', 'not in', [275,156])], limit=2):
            _logger.info("_do_fix_compute_overtime: checking employee '%s':" % emp_id.name)
            att_ids = self.env['hr.attendance'].search([('employee_id', '=', emp_id.id)])
            attendance_days_iso = [day.date().isoformat() for day in att_ids.mapped('check_in')]

            overtime_ids = self.env['hr.attendance.overtime'].search([('employee_id', '=', emp_id.id)])
            overtime_days_iso = [day.isoformat() for day in overtime_ids.mapped('date')]

            list_days_to_check = attendance_days_iso + overtime_days_iso

            days_to_check = [
                day for day in days_of_year_until_today if day not in list_days_to_check
            ]
            for day in days_to_check:
                # compute theoretical hours
                th = self.env['hr.attendance.theoretical.time.report']._theoretical_hours(
                    emp_id.sudo(), fields.Date.from_string(day)
                )
                if th > 0:
                    str_result += "employee: %s | day: %s | th: %s \n" % (emp_id.name, day, str(th))
                    fixing_att_id = self._create_overtime_fixing_attendance(emp_id, day)

        path_odoo_module = Path(os.path.dirname(os.path.abspath(__file__))).parent
        file = "files/overtime_check_%s.txt" % (datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        path_file_export = os.path.join(path_odoo_module, file)
        with open(path_file_export, 'w') as file:
            file.write(str_result)
        _logger.info("_do_fix_compute_overtime: finish")
