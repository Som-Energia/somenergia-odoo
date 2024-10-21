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

        Department = cls.env['hr.department'].with_context(tracking_disable=True)

        cls.dept_hr = Department.create({
            'name': 'Human Resources',
        })
        cls.dept_rd = Department.create({
            'name': 'Research and devlopment',
        })

        cls.default_calendar = cls.env['resource.calendar'].create({
            'name': 'moon calendar',
        })

        cls.company = cls.env['res.company'].create({
            'name': 'super company',
            'resource_calendar_id': cls.default_calendar.id,
        })

        cls.employee_user = new_test_user(
            cls.env, login='user', groups='base.group_user',
            company_ids=[(6, 0, cls.company.ids)], company_id=cls.company.id
        )
        cls.manager_user = new_test_user(
            cls.env, login='manager', groups='base.group_user,hr_holidays.group_hr_holidays_manager',
            company_ids=[(6, 0, cls.company.ids)], company_id=cls.company.id
        )

        cls.employee_emp = cls.env['hr.employee'].create({
            'name': 'Toto Employee',
            'company_id': cls.company.id,
            'user_id': cls.employee_user.id,
            'resource_calendar_id': cls.default_calendar.id,
            'department_id': cls.dept_hr.id
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
            'start_date': datetime(2024, 11, 2),
            'end_date': datetime(2024, 11, 2),
            'color': 1,
            'resource_calendar_id': cls.default_calendar.id,
        })
        cls.stress_week = cls.env['hr.leave.stress.day'].create({
            'name': 'Super Event End Of Week',
            'company_id': cls.company.id,
            'start_date': datetime(2024, 11, 8),
            'end_date': datetime(2024, 11, 12),
            'color': 2,
            'resource_calendar_id': cls.default_calendar.id,
        })

    @freeze_time('2024-10-15')
    def test_request_stress_days_with_restrictive_setting(self):
        self.company.som_restrictive_stress_days = True
        self.employee_user.resource_calendar_id = self.default_calendar.id

        # An employee can request time off outside stress days
        self.env['hr.leave'].with_user(self.employee_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2024, 11, 3),
            'date_to': datetime(2024, 11, 3),
            'number_of_days': 1,
        })

        # Taking a time off during a Stress Day is not allowed for a simple employee...
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.employee_user.id).create({
                'name': 'coucou',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'date_from': datetime(2024, 11, 3),
                'date_to': datetime(2024, 11, 17),
                'number_of_days': 1,
            })

        with self.assertRaises(ValidationError):
            self.env['hr.leave'].with_user(self.employee_user.id).create({
                'name': 'coucou',
                'holiday_status_id': self.leave_type.id,
                'employee_id': self.employee_emp.id,
                'date_from': datetime(2024, 11, 9),
                'date_to': datetime(2024, 11, 9),
                'number_of_days': 1,
            })

        # ... but is allowed for a Time Off Officer
        self.env['hr.leave'].with_user(self.manager_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2024, 11, 2),
            'date_to': datetime(2024, 11, 2),
            'number_of_days': 1,
        })

    @freeze_time('2024-10-15')
    def test_request_stress_days_with_no_restrictive_setting(self):
        self.company.som_restrictive_stress_days = False
        self.employee_user.resource_calendar_id = self.default_calendar.id

        # An employee can request time off outside stress days
        self.env['hr.leave'].with_user(self.employee_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2024, 11, 3),
            'date_to': datetime(2024, 11, 3),
            'number_of_days': 1,
        })

        # Taking a time off during a Stress Day is allowed for a simple employee...
        self.env['hr.leave'].with_user(self.employee_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2024, 11, 3),
            'date_to': datetime(2024, 11, 17),
            'number_of_days': 1,
        })

        self.env['hr.leave'].with_user(self.employee_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2024, 11, 2),
            'date_to': datetime(2024, 11, 2),
            'number_of_days': 1,
        })

        # ... and is allowed for a Time Off Officer
        self.env['hr.leave'].with_user(self.manager_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2024, 11, 2),
            'date_to': datetime(2024, 11, 2),
            'number_of_days': 1,
        })

    @freeze_time('2024-10-15')
    def test_get_leaves_stress_day_no_service_without_departments(self):
        self.company.som_restrictive_stress_days = False
        self.employee_user.write({
            'resource_calendar_id': self.default_calendar.id,
        })

        leaves_prev = self.env['hr.leave'].get_leaves('2024-11-01', '2024-11-15')

        new_sd_without_department = self.env['hr.leave.stress.day'].create({
            'name': 'Super New Event',
            'company_id': self.company.id,
            'start_date': datetime(2024, 11, 5),
            'end_date': datetime(2024, 11, 5),
            'color': 1,
            'resource_calendar_id': self.default_calendar.id,
            'som_type': 'no_service',
        })

        self.env['hr.leave'].with_user(self.employee_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2024, 11, 3),
            'date_to': datetime(2024, 11, 3),
            'number_of_days': 1,
        })
        
        leaves_post = self.env['hr.leave'].get_leaves('2024-11-01', '2024-11-15')
        self.assertEqual(len(leaves_post), len(leaves_prev) + 1)

    @freeze_time('2024-10-15')
    def test_get_leaves_stress_no_service_day_with_departments_same_dep(self):
        self.company.som_restrictive_stress_days = False
        self.employee_user.write({
            'resource_calendar_id': self.default_calendar.id,
        })
        self.employee_emp.write({
            'department_id': self.dept_rd.id,
        })
        self.manager_emp.write({
            'department_id': self.dept_rd.id,
        })

        leaves_prev = self.env['hr.leave'].get_leaves('2024-11-01', '2024-11-15')

        self.env['hr.leave.stress.day'].create({
            'name': 'Super New Event',
            'company_id': self.company.id,
            'start_date': datetime(2024, 11, 5),
            'end_date': datetime(2024, 11, 5),
            'color': 1,
            'resource_calendar_id': self.default_calendar.id,
            'department_ids': [(6, 0, [self.dept_rd.id])],
            'som_type': 'no_service',
        })

        self.env['hr.leave'].with_user(self.employee_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2024, 11, 3),
            'date_to': datetime(2024, 11, 3),
            'number_of_days': 1,
        })

        dict_leave_emp_sd = {
            'worker': self.employee_emp.user_id.email,
            'start_time': datetime(2024, 11, 5,7, 0, 0),
            'end_time': datetime(2024, 11, 5, 14, 0, 0),
        }
        dict_leave_manager_sd = {
            'worker': self.manager_emp.user_id.email,
            'start_time': datetime(2024, 11, 5, 7, 0, 0),
            'end_time': datetime(2024, 11, 5, 14, 0, 0),
        }

        leaves_post = self.env['hr.leave'].get_leaves('2024-11-01', '2024-11-15')
        self.assertEqual(len(leaves_post), len(leaves_prev) + 3)
        self.assertIn(dict_leave_emp_sd, leaves_post)
        self.assertIn(dict_leave_manager_sd, leaves_post)

    @freeze_time('2024-10-15')
    def test_get_leaves_stress_no_service_day_with_departments_different_dep(self):
        self.company.som_restrictive_stress_days = False
        self.employee_user.write({
            'resource_calendar_id': self.default_calendar.id,
        })
        self.employee_emp.write({
            'department_id': self.dept_rd.id,
        })
        self.manager_emp.write({
            'department_id': self.dept_hr.id,
        })

        leaves_prev = self.env['hr.leave'].get_leaves('2024-11-01', '2024-11-15')

        self.env['hr.leave.stress.day'].create({
            'name': 'Super New Event',
            'company_id': self.company.id,
            'start_date': datetime(2024, 11, 5),
            'end_date': datetime(2024, 11, 5),
            'color': 1,
            'resource_calendar_id': self.default_calendar.id,
            'department_ids': [(6, 0, [self.dept_hr.id])],
            'som_type': 'no_service',
        })

        self.env['hr.leave'].with_user(self.employee_user.id).create({
            'name': 'coucou',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime(2024, 11, 3),
            'date_to': datetime(2024, 11, 3),
            'number_of_days': 1,
        })

        dict_leave_emp_sd = {
            'worker': self.employee_emp.user_id.email,
            'start_time': datetime(2024, 11, 5, 7, 0, 0),
            'end_time': datetime(2024, 11, 5, 14, 0, 0),
        }
        dict_leave_manager_sd = {
            'worker': self.manager_emp.user_id.email,
            'start_time': datetime(2024, 11, 5, 7, 0, 0),
            'end_time': datetime(2024, 11, 5, 14, 0, 0),
        }

        leaves_post = self.env['hr.leave'].get_leaves('2024-11-01', '2024-11-15')
        self.assertEqual(len(leaves_post), len(leaves_prev) + 2)
        self.assertNotIn(dict_leave_emp_sd, leaves_post)
        self.assertIn(dict_leave_manager_sd, leaves_post)
