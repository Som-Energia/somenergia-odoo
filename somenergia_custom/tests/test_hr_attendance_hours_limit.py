# -*- coding: utf-8 -*-
import pytz
from datetime import datetime
from freezegun import freeze_time
from odoo.tests import common, new_test_user
from odoo.tests.common import tagged, TransactionCase
from odoo.exceptions import ValidationError, AccessError
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged('som_attendance_hours_limit')
class TestHrAttendanceHoursLimit(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        resource_calendar = cls.env["resource.calendar"]

        cls.calendar1 = resource_calendar.create(
            {"name": "Test calendar 1"}
        )

        cls.employee_user = new_test_user(
            cls.env, login='user',
            groups='hr_attendance.group_hr_attendance,hr_attendance.group_hr_attendance_kiosk',
            tz='Europe/Brussels',
        )
        cls.employee_emp = cls.env['hr.employee'].create({
            'name': 'Toto Employee',
            'user_id': cls.employee_user.id,
            'country_id': cls.env.ref("base.es").id,
            'tz': 'Europe/Brussels',
        })

        cls.employee_user_manager = new_test_user(
            cls.env, login='user_manager',
            groups='hr_attendance.group_hr_attendance,hr_attendance.group_hr_attendance_user',
            tz='Europe/Brussels',
        )
        cls.employee_manager = cls.env['hr.employee'].create({
            'name': 'Manager Employee',
            'user_id': cls.employee_user_manager.id,
            'country_id': cls.env.ref("base.es").id,
            'tz': 'Europe/Brussels',
        })

        cls.env.company.som_attendance_limit_checkin = 6
        cls.env.company.som_attendance_limit_checkout = 22

    def _tz_datetime(self, year, month, day, hour, minute):
        tz = pytz.timezone('Europe/Brussels')
        return tz.localize(datetime(year, month, day, hour, minute)).astimezone(pytz.utc).replace(tzinfo=None)

    @freeze_time('2025-03-06 6:00:00')
    def test_ahl_raise_before_checkin_limit(self):
        year_aux, month_aux, day_aux = (2025, 3, 6)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        with self.assertRaises(ValidationError):
            self.env['hr.attendance'].with_user(self.employee_user.id).create({
                'employee_id': self.employee_emp.id,
                'check_in': self._tz_datetime(year_aux, month_aux, day_aux, 5, 50),
            })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

    @freeze_time('2025-03-06 6:00:00')
    def test_ahl_noraise_checkin_limit(self):
        year_aux, month_aux, day_aux = (2025, 3, 6)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': self._tz_datetime(year_aux, month_aux, day_aux, 6, 50),
        })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)

    @freeze_time('2025-03-06 18:00:00')
    def test_ahl_raise_after_checkout_limit(self):
        year_aux, month_aux, day_aux = (2025, 3, 6)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)
        
        att_id = self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': self._tz_datetime(year_aux, month_aux, day_aux, 17, 50),
        })

        with self.assertRaises(ValidationError):
            att_id.write({
                'check_out': self._tz_datetime(year_aux, month_aux, day_aux, 22, 1),
            })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)
        self.assertEqual(att_id.check_out, False)

    @freeze_time('2025-03-06 20:00:00')
    def test_ahl_noraise_checkout_limit(self):
        year_aux, month_aux, day_aux = (2025, 3, 6)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        att_id = self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': self._tz_datetime(year_aux, month_aux, day_aux, 17, 50),
        })

        att_id.write({
            'check_out': self._tz_datetime(year_aux, month_aux, day_aux, 19, 50),
        })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)
        self.assertNotEqual(att_id.check_out, False)
