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
