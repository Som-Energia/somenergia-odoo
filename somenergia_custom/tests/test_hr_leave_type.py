# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.mail.tests.common import mail_new_test_user
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
            'request_date_from': leave_start_datetime.date(),
            'request_date_to': leave_end_datetime.date(),
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
            'request_date_from': leave_start_datetime_2.date(),
            'request_date_to': leave_end_datetime_2.date(),
            'number_of_days': (leave_end_datetime_2 - leave_start_datetime_2).days,
        })

        cls.user_employee2 = mail_new_test_user(cls.env, login='pere', groups='base.group_user')
        cls.employee_emp2 = cls.env['hr.employee'].create({
            'name': 'Pere Employee',
            'user_id': cls.user_employee2.id,
            'department_id': cls.rd_dept.id,
        })

        cls.holiday_3 = cls.env['hr.leave'].with_context(
            mail_create_nolog=True, mail_notrack=True
        ).with_user(cls.employee_emp2).create({
            'name': 'Leave 3',
            'employee_id': cls.employee_emp2.id,
            'holiday_status_id': cls.hr_leave_type_2.id,
            'date_from': leave_start_datetime_2,
            'date_to': leave_end_datetime_2,
            'request_date_from': leave_start_datetime_2.date(),
            'request_date_to': leave_end_datetime_2.date(),
            'number_of_days': (leave_end_datetime_2 - leave_start_datetime_2).days,
        })

        cls.env['hr.leave.type'].search([]).write({'som_eoa_notification_mail': False})

    # get_days_notify_types

    @freeze_time('2024-11-20')
    def test_get_days_notify_types__no_leave_types_with_notification(self):
        result = self.env['hr.leave.type'].get_days_notify_types()
        self.assertEqual(result, {})

    @freeze_time('2024-11-20')
    def test_get_days_notify_types__1_leave_type_with_notification(self):
        self.hr_leave_type_1.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 2,
        })
        result = self.env['hr.leave.type'].get_days_notify_types()
        self.assertEqual(result, {2: [self.hr_leave_type_1.id]})

    @freeze_time('2024-11-20')
    def test_get_days_notify_types__2_leave_type_with_notification_same_days(self):
        self.hr_leave_type_1.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 2,
        })
        self.hr_leave_type_2.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 2,
        })
        result = self.env['hr.leave.type'].get_days_notify_types()
        self.assertEqual(result, {2: sorted([self.hr_leave_type_1.id, self.hr_leave_type_2.id])})

    @freeze_time('2024-11-20')
    def test_get_days_notify_types__2_leave_type_with_notification_different_days(self):
        self.hr_leave_type_1.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 2,
        })
        self.hr_leave_type_2.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 3,
        })
        result = self.env['hr.leave.type'].get_days_notify_types()
        self.assertEqual(
            result, {2: [self.hr_leave_type_1.id], 3: [self.hr_leave_type_2.id]}
        )

    @freeze_time('2024-11-20')
    def test_get_days_notify_types__3_leave_type_with_notification_1_different_2_same_days(self):
        self.hr_leave_type_1.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 2,
        })
        self.hr_leave_type_2.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 3,
        })
        self.hr_leave_type_3.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 3,
        })
        result = self.env['hr.leave.type'].get_days_notify_types()
        self.assertEqual(
            result, {2: [self.hr_leave_type_1.id],
                     3: sorted([self.hr_leave_type_2.id, self.hr_leave_type_3.id])}
        )

    # get_absences_end_in_days

    @freeze_time('2024-11-20')
    def test_get_absences_end_in_days__10_days_to_end(self):
        absence_ids = self.hr_leave_type_1.get_absences_end_in_days(10)
        self.assertIn(self.holiday_1.id, absence_ids.ids)

    @freeze_time('2024-11-20')
    def test_get_absences_end_in_days__3_days_to_end(self):
        absence_ids = self.hr_leave_type_2.get_absences_end_in_days(3)
        self.assertIn(self.holiday_2.id, absence_ids.ids)
        self.assertIn(self.holiday_3.id, absence_ids.ids)

    @freeze_time('2024-11-20')
    def test_get_absences_end_in_days__5_days_to_end(self):
        absence_ids = self.hr_leave_type_1.get_absences_end_in_days(5)
        self.assertNotIn(self.holiday_1.id, absence_ids.ids)

        absence_ids = self.hr_leave_type_2.get_absences_end_in_days(5)
        self.assertNotIn(self.holiday_2.id, absence_ids.ids)

    # get_end_of_absences_mail_text

    @freeze_time('2024-11-20')
    def test_get_end_of_absences_mail_text__10_days_to_end(self):
        total_to_notify, str_msg = self.env['hr.leave.type'].get_end_of_absences_mail_text()
        self.assertEqual(total_to_notify, 0)

        self.hr_leave_type_1.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 10,
        })
        total_to_notify, str_msg = self.env['hr.leave.type'].get_end_of_absences_mail_text()
        self.assertEqual(total_to_notify, 1)

        self.assertIn('<strong>Absències que finalitzen en 10 dies', str_msg)

        msg_type_count = f'<br/><br/>{self.hr_leave_type_1.name} [1]<br/>'
        self.assertIn(msg_type_count, str_msg)

        msg_absence_name_get = f'<br/>{self.holiday_1.name_get()[0][1]}'
        self.assertIn(msg_absence_name_get, str_msg)

    @freeze_time('2024-11-20')
    def test_get_end_of_absences_mail_text__3_days_to_end(self):
        total_to_notify, str_msg = self.env['hr.leave.type'].get_end_of_absences_mail_text()
        self.assertEqual(total_to_notify, 0)

        self.hr_leave_type_2.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 3,
        })
        total_to_notify, str_msg = self.env['hr.leave.type'].get_end_of_absences_mail_text()
        self.assertEqual(total_to_notify, 2)

        self.assertIn('<strong>Absències que finalitzen en 3 dies', str_msg)

        msg_type_count = f'<br/><br/>{self.hr_leave_type_2.name} [2]<br/>'
        self.assertIn(msg_type_count, str_msg)

        msg_absence_name_get = f'<br/>{self.holiday_2.name_get()[0][1]}'
        self.assertIn(msg_absence_name_get, str_msg)

        msg_absence_name_get = f'<br/>{self.holiday_3.name_get()[0][1]}'
        self.assertIn(msg_absence_name_get, str_msg)

    @freeze_time('2024-11-20')
    def test_get_end_of_absences_mail_text__5_days_to_end(self):
        total_to_notify, str_msg = self.env['hr.leave.type'].get_end_of_absences_mail_text()
        self.assertEqual(total_to_notify, 0)

        self.hr_leave_type_1.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 5,
        })

        self.hr_leave_type_2.write({
            'som_eoa_notification_mail': True,
            'som_eoa_notification_days': 5,
        })

        total_to_notify, str_msg = self.env['hr.leave.type'].get_end_of_absences_mail_text()
        self.assertEqual(total_to_notify, 0)

        self.assertIn('<strong>Absències que finalitzen en 5 dies', str_msg)

        msg_type_count = f'<br/><br/>{self.hr_leave_type_1.name} [0]<br/>'
        self.assertIn(msg_type_count, str_msg)

        msg_type_count = f'<br/><br/>{self.hr_leave_type_2.name} [0]<br/>'
        self.assertIn(msg_type_count, str_msg)

        msg_absence_name_get = f'<br/>{self.holiday_1.name_get()[0][1]}'
        self.assertNotIn(msg_absence_name_get, str_msg)

        msg_absence_name_get = f'<br/>{self.holiday_2.name_get()[0][1]}'
        self.assertNotIn(msg_absence_name_get, str_msg)

        msg_absence_name_get = f'<br/>{self.holiday_3.name_get()[0][1]}'
        self.assertNotIn(msg_absence_name_get, str_msg)
