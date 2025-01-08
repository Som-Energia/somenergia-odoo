# -*- coding: utf-8 -*-

import pytz
from freezegun import freeze_time
from datetime import datetime
from unittest.mock import patch

from odoo import fields, _
from odoo.tests import common, new_test_user
from odoo.tests.common import tagged, TransactionCase
from odoo.exceptions import ValidationError
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT

@tagged('som_attendance_overtime')
class TestHrAttendanceOvertime(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        resource_calendar = cls.env["resource.calendar"]

        # 7 hours_per_day by default
        cls.calendar1 = resource_calendar.create(
            {"name": "Test calendar 1"}
        )

        cls.employee_user = new_test_user(
            cls.env, login='user', groups='base.group_user', tz='Europe/Brussels',
        )

        cls.employee_emp = cls.env['hr.employee'].create({
            'name': 'Toto Employee',
            'user_id': cls.employee_user.id,
            'country_id': cls.env.ref("base.es").id,
            'tz': 'Europe/Brussels',
        })

        cls.employee_emp.write({"calendar_ids": [(2, cls.employee_emp.calendar_ids.id)]})
        cls.employee_emp.calendar_ids = [
            (0, 0, {"date_start": "2025-01-01", "calendar_id": cls.calendar1.id}),
        ]
        cls.employee_emp._compute_current_calendar()

    def _tz_datetime(self, year, month, day, hour, minute):
        tz = pytz.timezone('Europe/Brussels')
        return tz.localize(datetime(year, month, day, hour, minute)).astimezone(pytz.utc).replace(tzinfo=None)

    def test_restrictive_overtime_setup_disabled(self):
        """ no restriction """
        self.env.company.som_restrictive_overtime = False
        year_aux, month_aux, day_aux = (2025, 1, 2)

        # 3 hours attendance
        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            'check_out': datetime(year_aux, month_aux, day_aux, 10, 10),
        })

        # 6 hours attendance
        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 11, 15),
            'check_out': datetime(year_aux, month_aux, day_aux, 17, 15),
        })

        with patch.object(fields.Datetime, 'now', lambda: self._tz_datetime(year_aux, month_aux, day_aux, 18, 0).astimezone(pytz.utc).replace(tzinfo=None)):
            self.assertEqual(self.employee_emp.hours_today, 9, "It should have counted 9 hours")

    def test_restrictive_overtime_setup_enabled__max_hours_today(self):
        """ assuming max_hours_today = 8 (7 + 1) """
        self.env.company.som_restrictive_overtime = True
        year_aux, month_aux, day_aux = (2025, 1, 2)

        # 3 hours attendance (so far hours_today = 3)
        att1_id = self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            'check_out': datetime(year_aux, month_aux, day_aux, 10, 10),
        })

        self.assertEqual(att1_id.get_max_hours_today(), 8)

    def test_restrictive_overtime_setup_enabled__att_1_extra_hour_allowed(self):
        """
        max_hours_today = 8 (7 + 1)
        check_in and check_out in UTC
        """
        self.env.company.som_restrictive_overtime = True
        year_aux, month_aux, day_aux = (2025, 1, 2)

        # 3 hours attendance (so far hours_today = 3)
        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            'check_out': datetime(year_aux, month_aux, day_aux, 10, 10),
        })

        # 4:45 hours attendance (so far hours_today = 7:45)
        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 11, 00),
            'check_out': datetime(year_aux, month_aux, day_aux, 15, 45),
        })

        # new 1 hours attendance to exceed 8 hours_today and to force to raise the exception
        with self.assertRaises(ValidationError) as context:
            self.env['hr.attendance'].create({
                'employee_id': self.employee_emp.id,
                'check_in': datetime(year_aux, month_aux, day_aux, 16, 00),
                'check_out': datetime(year_aux, month_aux, day_aux, 17, 00),
            })

        error_msg = _("L'hora màxima per tancar l'assistència és 02/01/2025 17:15:00 ")
        self.assertEqual(str(context.exception), error_msg)

        with patch.object(fields.Datetime, 'now',
                          lambda: self._tz_datetime(year_aux, month_aux, day_aux, 19, 0).astimezone(
                                  pytz.utc).replace(tzinfo=None)):
            self.assertEqual(self.employee_emp.hours_today, 7.75, "It should have counted 7.75 hours")

    def test_restrictive_overtime_setup_enabled__att_2_extra_hours_allowed(self):
        """
        max_hours_today = 8 (7 + 1)
        check_in and check_out in UTC
        """
        self.env.company.som_restrictive_overtime = True
        self.calendar1.write({'som_max_overtime_per_day': 2}) # max_hours_today = 9 (7 + 2)

        self.assertEqual(self.calendar1.som_max_overtime_per_day, 2)
        self.assertEqual(self.employee_emp.sudo().som_current_calendar_id.id, self.calendar1.id)

        year_aux, month_aux, day_aux = (2025, 1, 2)

        # 3 hours attendance (so far hours_today = 3)
        att1_id = self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 0),
            'check_out': datetime(year_aux, month_aux, day_aux, 10, 0),
        })
        self.assertEqual(att1_id.get_max_hours_today(), 9)

        # 5:30 hours attendance (so far hours_today = 8:30)
        att2_id = self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 11, 00),
            'check_out': datetime(year_aux, month_aux, day_aux, 16, 30),
        })
        self.assertEqual(att2_id.get_max_hours_today(), 9)

        # new 1 hours attendance to exceed 9 hours_today and to force to raise the exception
        with self.assertRaises(ValidationError) as context:
            self.env['hr.attendance'].create({
                'employee_id': self.employee_emp.id,
                'check_in': datetime(year_aux, month_aux, day_aux, 17, 00),
                'check_out': datetime(year_aux, month_aux, day_aux, 18, 00),
            })

        error_msg = _("L'hora màxima per tancar l'assistència és 02/01/2025 18:30:00 ")
        self.assertEqual(str(context.exception), error_msg)

        with patch.object(fields.Datetime, 'now',
                          lambda: self._tz_datetime(year_aux, month_aux, day_aux, 19, 0).astimezone(
                              pytz.utc).replace(tzinfo=None)):
            self.assertEqual(self.employee_emp.hours_today, 8.5, "It should have counted 8.5 hours")

    @freeze_time('2025-01-02 18:00:00')
    def test_restrictive_overtime_setup_enabled__checkout_forced(self):
        """ assuming max_hours_today = 8 (7 + 1) """
        self.env.company.som_restrictive_overtime = True
        year_aux, month_aux, day_aux = (2025, 1, 2)

        # 3 hours attendance (so far hours_today = 3)
        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            'check_out': datetime(year_aux, month_aux, day_aux, 10, 10),
        })

        # 4:45 hours attendance (so far hours_today = 7:45)
        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 11, 00),
            'check_out': datetime(year_aux, month_aux, day_aux, 15, 45),
        })

        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 16, 00),
        })
        self.assertEqual(self.employee_emp.attendance_state, 'checked_in')

        with patch(
                'odoo.addons.somenergia_custom.models.hr_attendance.HrAttendance.send_mail_attendance_reminder'
        ) as mock_send_mail_attendance_reminder:
            att_3_id = self.employee_emp._attendance_action_change()
            mock_send_mail_attendance_reminder.assert_called_once()
            mock_send_mail_attendance_reminder.assert_called_with(
                att_3_id,
                datetime(year_aux, month_aux, day_aux, 18, 00),
                datetime(year_aux, month_aux, day_aux, 16, 15),
            )
        self.assertEqual(self.employee_emp.attendance_state, 'checked_out')
        self.assertIsNotNone(att_3_id)
        self.assertEqual(att_3_id.check_out, datetime(year_aux, month_aux, day_aux, 16, 15))
        self.assertEqual(att_3_id.get_max_hours_today(), self.employee_emp.hours_today)

    @freeze_time('2025-01-02 16:10:00')
    def test_restrictive_overtime_setup_enabled__checkout_ok(self):
        """ assuming max_hours_today = 8 (7 + 1) """
        self.env.company.som_restrictive_overtime = True
        year_aux, month_aux, day_aux = (2025, 1, 2)

        # 3 hours attendance (so far hours_today = 3)
        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            'check_out': datetime(year_aux, month_aux, day_aux, 10, 10),
        })

        # 4:45 hours attendance (so far hours_today = 7:45)
        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 11, 00),
            'check_out': datetime(year_aux, month_aux, day_aux, 15, 45),
        })

        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 16, 00),
        })
        self.assertEqual(self.employee_emp.attendance_state, 'checked_in')

        with patch(
                'odoo.addons.somenergia_custom.models.hr_attendance.HrAttendance.send_mail_attendance_reminder'
        ) as mock_send_mail_attendance_reminder:
            att_3_id = self.employee_emp._attendance_action_change()
            mock_send_mail_attendance_reminder.assert_not_called()
        self.assertEqual(self.employee_emp.attendance_state, 'checked_out')
        self.assertIsNotNone(att_3_id)
        self.assertEqual(att_3_id.check_out, datetime(year_aux, month_aux, day_aux, 16, 10))

    @freeze_time('2025-01-02 18:00:00')
    def test_restrictive_overtime_setup_disabled__checkout_ok(self):
        """ assuming max_hours_today = 8 (7 + 1) """
        self.env.company.som_restrictive_overtime = False
        year_aux, month_aux, day_aux = (2025, 1, 2)

        # 3 hours attendance (so far hours_today = 3)
        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            'check_out': datetime(year_aux, month_aux, day_aux, 10, 10),
        })

        # 4:45 hours attendance (so far hours_today = 7:45)
        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 11, 00),
            'check_out': datetime(year_aux, month_aux, day_aux, 15, 45),
        })

        # 2 hours attendance (so far hours_today = 9:45)
        self.env['hr.attendance'].create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 16, 00),
        })
        self.assertEqual(self.employee_emp.attendance_state, 'checked_in')

        with patch(
                'odoo.addons.somenergia_custom.models.hr_attendance.HrAttendance.send_mail_attendance_reminder'
        ) as mock_send_mail_attendance_reminder:
            att_3_id = self.employee_emp._attendance_action_change()
            mock_send_mail_attendance_reminder.assert_not_called()

        self.assertEqual(self.employee_emp.attendance_state, 'checked_out')
        self.assertIsNotNone(att_3_id)
        self.assertEqual(att_3_id.check_out, datetime(year_aux, month_aux, day_aux, 18, 00))
        self.assertEqual(self.employee_emp.hours_today, 9.75, "It should have counted 9.75 hours")
