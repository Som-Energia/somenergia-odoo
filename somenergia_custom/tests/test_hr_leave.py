# -*- coding: utf-8 -*-
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.tests.common import tagged, Form


@tagged('som_hr_leave')
class TestHrLeave(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.hr_leave_type = cls.env['hr.leave.type'].with_user(cls.user_hrmanager).create({
            'name': 'Leave Type',
        })

    def test_absence_description_no_mandatory(self):
        absence_form = Form(self.env["hr.leave"].with_user(
            self.employee_emp.user_id.id), view="hr_holidays.hr_leave_view_form"
        )
        absence_form.holiday_status_id = self.hr_leave_type
        absence_form.save()

    def test_absence_description_mandatory(self):
        self.hr_leave_type.write({'som_mandatory_description': True})
        absence_form = Form(self.env["hr.leave"].with_user(
            self.employee_emp.user_id.id), view="hr_holidays.hr_leave_view_form"
        )
        absence_form.holiday_status_id = self.hr_leave_type
        with self.assertRaises(AssertionError):
            absence_form.save()
