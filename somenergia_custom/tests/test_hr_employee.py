# -*- coding: utf-8 -*-
import pytz
from freezegun import freeze_time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tests import common, new_test_user
from odoo.tests.common import tagged, TransactionCase
from odoo.exceptions import ValidationError, AccessError
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('employee_is_present')
class TestEmployeeIsPresent(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        leave_start_datetime = datetime(2025, 4, 1, 8, 0, 0, 0)
        leave_end_datetime = datetime(2025, 4, 3, 15, 0, 0, 0)
        # leave_end_datetime = leave_start_datetime + relativedelta(days=2)

        leave_start_datetime_2 = datetime(2025, 4, 1, 7, 0, 0, 0)
        leave_end_datetime_2 = datetime(2025, 4, 1, 15, 0, 0, 0)
        # leave_end_datetime_2 = leave_start_datetime_2 + relativedelta(days=0)

        cls.hr_leave_type_1 = cls.env['hr.leave.type'].with_user(cls.user_hrmanager).create({
            'name': 'Leave Type 1',
        })

        cls.holiday_1 = cls.env['hr.leave'].with_context(
            mail_create_nolog=True, mail_notrack=True
        ).with_user(cls.user_employee).create({
            'name': 'Leave 1',
            'employee_id': cls.employee_emp.id,
            'holiday_status_id': cls.hr_leave_type_1.id,
            'date_from': leave_start_datetime,
            'date_to': leave_end_datetime,
            'number_of_days': 3,
        })
        cls.holiday_1.with_user(cls.user_hrmanager).action_validate()

        cls.user_employee2 = new_test_user(cls.env, login='pere', groups='base.group_user')
        cls.employee_emp2 = cls.env['hr.employee'].create({
            'name': 'Pere Employee',
            'user_id': cls.user_employee2.id,
            'department_id': cls.rd_dept.id,
        })

        cls.holiday_2 = cls.env['hr.leave'].with_context(
            mail_create_nolog=True, mail_notrack=True
        ).with_user(cls.user_employee2).create({
            'name': 'Leave 2',
            'employee_id': cls.employee_emp2.id,
            'holiday_status_id': cls.hr_leave_type_1.id,
            'date_from': leave_start_datetime_2,
            'date_to': leave_end_datetime_2,
            'number_of_days': 1,
        })

        cls.env['hr.leave.type'].search([]).write({'som_eoa_notification_mail': False})

    def _tz_datetime(self, year, month, day, hour, minute):
        tz = pytz.timezone('Europe/Brussels')
        return tz.localize(datetime(year, month, day, hour, minute)).astimezone(pytz.utc).replace(tzinfo=None)

    @freeze_time('2025-04-01 06:00:00')
    def test_is_present_search_both_no_present(self):
        present_emp_ids = self.env['hr.employee'].search([("is_present", "=", True)])
        self.assertNotIn(self.employee_emp.id, present_emp_ids.ids, "Value should not be in the list")
        self.assertNotIn(self.employee_emp2.id, present_emp_ids.ids, "Value should not be in the list")

    @freeze_time('2025-04-02 06:00:00')
    def test_is_present_search_just_one_present(self):
        present_emp_ids = self.env['hr.employee'].search([("is_present", "=", True)])
        self.assertNotIn(self.employee_emp.id, present_emp_ids.ids, "Value should not be in the list")
        self.assertIn(self.employee_emp2.id, present_emp_ids.ids, "Value should be in the list")

    @freeze_time('2025-04-04 06:00:00')
    def test_is_present_search_both_present(self):
        present_emp_ids = self.env['hr.employee'].search([("is_present", "=", True)])
        self.assertIn(self.employee_emp.id, present_emp_ids.ids, "Value should be in the list")
        self.assertIn(self.employee_emp2.id, present_emp_ids.ids, "Value should be in the list")


@tagged('som_manager_ids')
class TestSomManagerIds(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.department_a = cls.env['hr.department'].create({
            'name': 'Department A',
        })

        cls.subdepartment_1 = cls.env['hr.department'].create({
            'name': 'Subdepartment 1',
            'parent_id': cls.department_a.id,
        })
        cls.subdepartment_2 = cls.env['hr.department'].create({
            'name': 'Subdepartment 2',
            'parent_id': cls.department_a.id,
        })

        cls.manager_dep = cls.env['hr.employee'].create({
            'name': 'Manager Dep',
            'department_id': cls.department_a.id,
        })
        cls.department_a.write({'manager_id': cls.manager_dep.id})

        cls.manager_1 = cls.env['hr.employee'].create({
            'name': 'Manager 1',
            'department_id': cls.department_a.id,
        })
        cls.manager_2 = cls.env['hr.employee'].create({
            'name': 'Manager 2',
            'department_id': cls.department_a.id,
        })

        cls.subdepartment_1.write({'manager_id': cls.manager_1.id})
        cls.subdepartment_2.write({'manager_id': cls.manager_2.id})

        cls.employee_in_department_a = cls.env['hr.employee'].create({
            'name': 'Employee A',
            'department_id': cls.department_a.id,
        })

        cls.department_b = cls.env['hr.department'].create({
            'name': 'Department B',
        })

        cls.employee_in_department_b = cls.env['hr.employee'].create({
            'name': 'Employee B',
            'department_id': cls.department_b.id,
        })

        cls.employee_without_department = cls.env['hr.employee'].create({
            'name': 'Employee No Dept',
        })

    def test_som_manager_ids_department_parent(self):
        self.employee_in_department_a._compute_som_manager_ids()
        managers = self.employee_in_department_a.som_manager_ids
        self.assertIn(self.manager_1, managers, "Manager 1 should be included")
        self.assertIn(self.manager_2, managers, "Manager 2 should be included")
        self.assertIn(self.manager_dep, managers, "Manager Dep should be included")

    def test_som_manager_ids_no_managers(self):
        self.employee_without_department._compute_som_manager_ids()
        self.assertFalse(self.employee_without_department.som_manager_ids, "Should be empty")

        self.employee_in_department_b._compute_som_manager_ids()
        self.assertFalse(self.employee_in_department_b.som_manager_ids, "Should be empty")
