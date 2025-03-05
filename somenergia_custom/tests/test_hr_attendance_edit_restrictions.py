# -*- coding: utf-8 -*-

import pytz
from freezegun import freeze_time
from datetime import datetime
from unittest.mock import patch

from odoo import fields, _
from odoo.tests import common, new_test_user
from odoo.tests.common import tagged, TransactionCase
from odoo.exceptions import ValidationError, AccessError
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged('som_attendance_edit_restrictions')
class TestHrAttendanceEditRestrictions(common.TransactionCase):
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

        rule_attendance_manual = cls.env.ref(
            'hr_attendance.hr_attendance_rule_attendance_manual', raise_if_not_found=False
        )
        rule_attendance_manual.write({
            'perm_read': True,
            'perm_write': False,
            'perm_create': False,
            'perm_unlink': False,
        })

    def _tz_datetime(self, year, month, day, hour, minute):
        tz = pytz.timezone('Europe/Brussels')
        return tz.localize(datetime(year, month, day, hour, minute)).astimezone(pytz.utc).replace(tzinfo=None)

    # CREATE
    # ---------------------------------
    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_disabled__create_no_raise(self):
        self.env.company.som_amend_attendance_restrictive = False
        self.env.company.som_amend_attendance_days_to = 0
        year_aux, month_aux, day_aux = (2025, 3, 3)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
        })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)

    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_enabled_create_raise_restriction(self):
        self.env.company.som_amend_attendance_restrictive = True
        self.env.company.som_amend_attendance_days_to = 0
        year_aux, month_aux, day_aux = (2025, 3, 3)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        with self.assertRaises(AccessError) as context:
            self.env['hr.attendance'].with_user(self.employee_user.id).create({
                'employee_id': self.employee_emp.id,
                'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        # Rule does not apply for attendance manager users
        self.env['hr.attendance'].with_user(self.employee_user_manager.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
        })
        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)

    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_enabled_create_no_raise_restriction(self):
        self.env.company.som_amend_attendance_restrictive = True
        self.env.company.som_amend_attendance_days_to = 0
        year_aux, month_aux, day_aux = (2025, 3, 4)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
        })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)

    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_enabled_create_2_days_margin_no_raise_restriction(self):
        self.env.company.som_amend_attendance_restrictive = True
        self.env.company.som_amend_attendance_days_to = 2
        year_aux, month_aux, day_aux = (2025, 3, 2)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
        })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)

    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_enabled_create_2_days_margin_raise_restriction(self):
        self.env.company.som_amend_attendance_restrictive = True
        self.env.company.som_amend_attendance_days_to = 2
        year_aux, month_aux, day_aux = (2025, 3, 1)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        with self.assertRaises(AccessError) as context:
            self.env['hr.attendance'].with_user(self.employee_user.id).create({
                'employee_id': self.employee_emp.id,
                'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

    # WRITE
    # ---------------------------------
    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_disabled__write_no_raise(self):
        self.env.company.som_amend_attendance_restrictive = False
        self.env.company.som_amend_attendance_days_to = 0
        year_aux, month_aux, day_aux = (2025, 2, 5)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        att_id = self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            'check_out': datetime(year_aux, month_aux, day_aux, 12, 45),
        })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)

        att_id.with_user(self.employee_user.id).write({
            'check_out': datetime(year_aux, month_aux, day_aux, 13, 45),
        })

    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_enabled__write_raise(self):
        self.env.company.som_amend_attendance_restrictive = False
        self.env.company.som_amend_attendance_days_to = 0
        year_aux, month_aux, day_aux = (2025, 3, 3)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        att_id = self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            'check_out': datetime(year_aux, month_aux, day_aux, 12, 45),
        })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)

        self.env.company.som_amend_attendance_restrictive = True

        with self.assertRaises(AccessError) as context:
            att_id.with_user(self.employee_user.id).write({
                'check_out': datetime(year_aux, month_aux, day_aux, 13, 45),
            })
        self.assertEqual(att_id.check_out, datetime(year_aux, month_aux, day_aux, 12, 45))

        # Rule does not apply for attendance manager users
        att_id.with_user(self.employee_user_manager.id).write({
            'check_out': datetime(year_aux, month_aux, day_aux, 13, 45),
        })
        self.assertEqual(att_id.check_out, datetime(year_aux, month_aux, day_aux, 13, 45))

    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_enabled__write_no_raise(self):
        self.env.company.som_amend_attendance_restrictive = False
        self.env.company.som_amend_attendance_days_to = 0
        year_aux, month_aux, day_aux = (2025, 3, 3)
        year_aux2, month_aux2, day_aux2 = (2025, 2, 28)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        att_id = self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            'check_out': datetime(year_aux, month_aux, day_aux, 12, 45),
        })

        att2_id = self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux2, month_aux2, day_aux2, 7, 10),
            'check_out': datetime(year_aux2, month_aux2, day_aux2, 12, 45),
        })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 2)

        self.env.company.som_amend_attendance_restrictive = True
        self.env.company.som_amend_attendance_days_to = 1

        att_id.with_user(self.employee_user.id).write({
            'check_out': datetime(year_aux, month_aux, day_aux, 13, 45),
        })
        self.assertEqual(att_id.check_out, datetime(year_aux, month_aux, day_aux, 13, 45))

        with self.assertRaises(AccessError) as context:
            att2_id.with_user(self.employee_user.id).write({
                'check_out': datetime(year_aux, month_aux, day_aux, 13, 45),
            })
        self.assertEqual(att2_id.check_out, datetime(year_aux2, month_aux2, day_aux2, 12, 45))

    # UNLINK
    # ---------------------------------
    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_disabled__unlink_no_raise(self):
        self.env.company.som_amend_attendance_restrictive = False
        self.env.company.som_amend_attendance_days_to = 0
        year_aux, month_aux, day_aux = (2025, 2, 5)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        att_id = self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            'check_out': datetime(year_aux, month_aux, day_aux, 12, 45),
        })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)

        att_id.with_user(self.employee_user.id).unlink()
        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_enabled__unlink_raise(self):
        self.env.company.som_amend_attendance_restrictive = False
        self.env.company.som_amend_attendance_days_to = 0
        year_aux, month_aux, day_aux = (2025, 3, 3)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        att_id = self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            'check_out': datetime(year_aux, month_aux, day_aux, 12, 45),
        })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)

        self.env.company.som_amend_attendance_restrictive = True

        with self.assertRaises(AccessError) as context:
            att_id.with_user(self.employee_user.id).unlink()
        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)

        # Rule does not apply for attendance manager users
        att_id.with_user(self.employee_user_manager.id).unlink()
        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_enabled__unlink_no_raise(self):
        self.env.company.som_amend_attendance_restrictive = False
        self.env.company.som_amend_attendance_days_to = 0
        year_aux, month_aux, day_aux = (2025, 3, 3)
        year_aux2, month_aux2, day_aux2 = (2025, 2, 28)

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 0)

        att_id = self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux, month_aux, day_aux, 7, 10),
            'check_out': datetime(year_aux, month_aux, day_aux, 12, 45),
        })

        att2_id = self.env['hr.attendance'].with_user(self.employee_user.id).create({
            'employee_id': self.employee_emp.id,
            'check_in': datetime(year_aux2, month_aux2, day_aux2, 7, 10),
            'check_out': datetime(year_aux2, month_aux2, day_aux2, 12, 45),
        })

        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 2)

        self.env.company.som_amend_attendance_restrictive = True
        self.env.company.som_amend_attendance_days_to = 1

        att_id.with_user(self.employee_user.id).unlink()
        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)

        with self.assertRaises(AccessError) as context:
            att2_id.with_user(self.employee_user.id).unlink()
        att_ids = self.env['hr.attendance'].search([('employee_id', '=', self.employee_emp.id)])
        self.assertEqual(len(att_ids), 1)
