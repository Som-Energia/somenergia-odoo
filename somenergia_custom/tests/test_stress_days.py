# -*- coding: utf-8 -*-
from datetime import datetime
from freezegun import freeze_time

from odoo import tests
from odoo.tests import new_test_user
from odoo.tests.common import Form, TransactionCase
from odoo.exceptions import ValidationError


@tests.tagged('access_rights', 'post_install', '-at_install')
class TestSomHrLeaveStressDays(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.default_calendar = cls.env['resource.calendar'].create({
            'name': 'moon calendar',
        })

        cls.company = cls.env['res.company'].create({
            'name': 'super company',
            'resource_calendar_id': cls.default_calendar.id,
        })

        cls.employee_user = new_test_user(cls.env, login='user', groups='base.group_user', company_ids=[(6, 0, cls.company.ids)], company_id=cls.company.id)
        cls.manager_user = new_test_user(cls.env, login='manager', groups='base.group_user,hr_holidays.group_hr_holidays_manager', company_ids=[(6, 0, cls.company.ids)], company_id=cls.company.id)

        cls.employee_emp = cls.env['hr.employee'].create({
            'name': 'Toto Employee',
            'company_id': cls.company.id,
            'user_id': cls.employee_user.id,
            'resource_calendar_id': cls.default_calendar.id,
        })
        cls.manager_emp = cls.env['hr.employee'].create({
            'name': 'Toto Mananger',
            'company_id': cls.company.id,
            'user_id': cls.manager_user.id,
        })

        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Unlimited',
            'leave_validation_type': 'hr',
            'requires_allocation': 'no',
            'company_id': cls.company.id,
        })

        cls.stress_day = cls.env['hr.leave.stress.day'].create({
            'name': 'Super Event',
            'company_id': cls.company.id,
            'start_date': datetime(2021, 11, 2),
            'end_date': datetime(2021, 11, 2),
            'color': 1,
            'resource_calendar_id': cls.default_calendar.id,
        })
        cls.stress_week = cls.env['hr.leave.stress.day'].create({
            'name': 'Super Event End Of Week',
            'company_id': cls.company.id,
            'start_date': datetime(2021, 11, 8),
            'end_date': datetime(2021, 11, 12),
            'color': 2,
            'resource_calendar_id': cls.default_calendar.id,
        })

    @freeze_time('2021-10-15')
    def test_request_stress_days_with_restrictive_setting(self):
        self.company.som_restrictive_stress_days = True
        self.employee_user.resource_calendar_id = self.default_calendar.id

        # An employee can request time off outside stress days
        self.env['hr.leave'].with_user(self.employee_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2021, 11, 3),
            'date_to': datetime(2021, 11, 3),
            'number_of_days': 1,
        })

        # Taking a time off during a Stress Day is not allowed for a simple employee...
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.employee_user.id).create({
                'name': 'coucou',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'date_from': datetime(2021, 11, 3),
                'date_to': datetime(2021, 11, 17),
                'number_of_days': 1,
            })

        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.employee_user.id).create({
                'name': 'coucou',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'date_from': datetime(2021, 11, 9),
                'date_to': datetime(2021, 11, 9),
                'number_of_days': 1,
            })

        # ... but is allowed for a Time Off Officer
        self.env['hr.leave'].with_user(self.manager_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2021, 11, 2),
            'date_to': datetime(2021, 11, 2),
            'number_of_days': 1,
        })

    @freeze_time('2021-10-15')
    def test_request_stress_days_with_no_restrictive_setting(self):
        self.company.som_restrictive_stress_days = False
        self.employee_user.resource_calendar_id = self.default_calendar.id

        # An employee can request time off outside stress days
        self.env['hr.leave'].with_user(self.employee_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2021, 11, 3),
            'date_to': datetime(2021, 11, 3),
            'number_of_days': 1,
        })

        # Taking a time off during a Stress Day is allowed for a simple employee...
        self.env['hr.leave'].with_user(self.employee_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2021, 11, 3),
            'date_to': datetime(2021, 11, 17),
            'number_of_days': 1,
        })

        # ... and is allowed for a Time Off Officer
        self.env['hr.leave'].with_user(self.manager_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2021, 11, 2),
            'date_to': datetime(2021, 11, 2),
            'number_of_days': 1,
        })
