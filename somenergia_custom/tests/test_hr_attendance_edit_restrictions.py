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

        # 7 hours_per_day by default
        cls.calendar1 = resource_calendar.create(
            {"name": "Test calendar 1"}
        )

        cls.employee_user = new_test_user(
            cls.env, login='user',
            groups='hr_attendance.group_hr_attendance,hr_attendance.group_hr_attendance_kiosk',
            tz='Europe/Brussels',
        )
        # hr_attendance.group_hr_attendance_kiosk

        cls.employee_emp = cls.env['hr.employee'].create({
            'name': 'Toto Employee',
            'user_id': cls.employee_user.id,
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

    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_disabled__create_no_raise(self):
        """ no restriction """
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
        """ no restriction """
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

    @freeze_time('2025-03-04 17:00:00')
    def test_rae__setup_enabled_create_no_raise_restriction(self):
        """ no restriction """
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
        """ no restriction """
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
        """ no restriction """
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
