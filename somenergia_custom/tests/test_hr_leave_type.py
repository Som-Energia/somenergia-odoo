# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.exceptions import UserError, ValidationError

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHrLeaveType(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        leave_start_datetime = datetime(2024, 11, 27, 7, 0, 0, 0)
        leave_end_datetime = leave_start_datetime + relativedelta(days=3)

        leave_start_datetime_2 = datetime(2024, 11, 21, 7, 0, 0, 0)
        leave_end_datetime_2 = leave_start_datetime_2 + relativedelta(days=2)

        cls.hr_leave_type_1 = cls.env['hr.leave.type'].with_user(cls.user_hrmanager).create({
            'name': 'Leave Type 1',
        })

        cls.hr_leave_type_2 = cls.env['hr.leave.type'].with_user(cls.user_hrmanager).create({
            'name': 'Leave Type 2',
        })

        cls.hr_leave_type_3 = cls.env['hr.leave.type'].with_user(cls.user_hrmanager).create({
            'name': 'Leave Type 3',
        })

        cls.holiday_1 = cls.env['hr.leave'].with_context(
            mail_create_nolog=True, mail_notrack=True
        ).with_user(cls.user_employee).create({
            'name': 'Leave 1',
            'employee_id': cls.employee_emp.id,
            'holiday_status_id': cls.hr_leave_type_1.id,
            'date_from': leave_start_datetime,
            'date_to': leave_end_datetime,
            'number_of_days': (leave_end_datetime - leave_start_datetime).days,
        })
        cls.holiday_1.with_user(cls.user_hrmanager).action_validate()

        cls.holiday_2 = cls.env['hr.leave'].with_context(
            mail_create_nolog=True, mail_notrack=True
        ).with_user(cls.user_employee).create({
            'name': 'Leave 2',
            'employee_id': cls.employee_emp.id,
            'holiday_status_id': cls.hr_leave_type_2.id,
            'date_from': leave_start_datetime_2,
            'date_to': leave_end_datetime_2,
            'number_of_days': (leave_end_datetime_2 - leave_start_datetime_2).days,
        })

        cls.env['hr.leave.type'].search([]).write({'som_eoa_notification_mail': False})

    @freeze_time('2024-11-20')
    def test_get_days_type(self):
        # {2: [11], 5: [7, 9]}

        # with no leave types with notification
        result = self.env['hr.leave.type'].get_days_type()
        self.assertEqual(result, {})

        # with 1 leave types with notification
        self.hr_leave_type_1.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 2,
        })
        result = self.env['hr.leave.type'].get_days_type()
        self.assertEqual(result, {2: [self.hr_leave_type_1.id]})

        # with 2 leave types with notification - same days
        self.hr_leave_type_2.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 2,
        })
        result = self.env['hr.leave.type'].get_days_type()
        self.assertEqual(result, {2: sorted([self.hr_leave_type_1.id, self.hr_leave_type_2.id])})

        # with 2 leave types with notification - different days
        self.hr_leave_type_2.write({
            'som_eoa_notification_days': 3,
        })
        result = self.env['hr.leave.type'].get_days_type()
        self.assertEqual(
            result, {2: [self.hr_leave_type_1.id], 3: [self.hr_leave_type_2.id]}
        )

        # with 3 leave types with notification - 1 different 2 same days
        self.hr_leave_type_3.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 3,
        })
        result = self.env['hr.leave.type'].get_days_type()
        self.assertEqual(
            result, {2: [self.hr_leave_type_1.id],
                     3: sorted([self.hr_leave_type_2.id, self.hr_leave_type_3.id])}
        )
