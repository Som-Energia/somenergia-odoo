# -*- coding: utf-8 -*-
from freezegun import freeze_time
from odoo.tests import common, new_test_user
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


class TestHrEmployeeCalendar(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        resource_calendar = cls.env["resource.calendar"]
        cls.calendar1 = resource_calendar.create(
            {"name": "Test calendar 1", "attendance_ids": []}
        )
        cls.calendar2 = resource_calendar.create(
            {"name": "Test calendar 2", "attendance_ids": []}
        )

        cls.employee = cls.env["hr.employee"].create({"name": "Test employee"})
        cls.employee2 = cls.env["hr.employee"].create({"name": "Test employee 2"})

        # By default a calendar_ids is set, we remove it to better clarify the tests.
        cls.employee.write({"calendar_ids": [(2, cls.employee.calendar_ids.id)]})

    @freeze_time('2024-10-15')
    def test_current_calendar__initial(self):
        self.employee.calendar_ids = [
            (0, 0, {"date_start": "2024-01-01", "calendar_id": self.calendar1.id}),
        ]
        self.assertTrue(self.employee.resource_calendar_id)
        self.assertTrue(self.employee.som_current_calendar_id)

    @freeze_time('2024-10-15')
    def test_current_calendar__when_change_no_end(self):
        self.employee.calendar_ids = [
            (0, 0, {"date_start": "2024-01-01", "date_end": "2024-09-30", "calendar_id": self.calendar1.id}),
        ]
        self.assertTrue(self.employee.resource_calendar_id)
        self.assertFalse(self.employee.som_current_calendar_id)

        self.employee.calendar_ids = [
            (0, 0, {"date_start": "2024-10-01", "calendar_id": self.calendar2.id}),
        ]
        self.assertTrue(self.employee.som_current_calendar_id)
        self.assertEqual(self.employee.som_current_calendar_id.id, self.calendar2.id)

    @freeze_time('2024-10-15')
    def test_current_calendar__start_and_future_end(self):
        self.employee.calendar_ids = [
            (0, 0, {"date_start": "2024-01-01", "date_end": "2024-09-30", "calendar_id": self.calendar1.id}),
        ]
        self.assertTrue(self.employee.resource_calendar_id)
        self.assertFalse(self.employee.som_current_calendar_id)

        self.employee.calendar_ids = [
            (0, 0, {"date_start": "2024-10-01", "date_end": "2024-12-31", "calendar_id": self.calendar2.id}),
        ]
        self.assertTrue(self.employee.som_current_calendar_id)
        self.assertEqual(self.employee.som_current_calendar_id.id, self.calendar2.id)

    @freeze_time('2024-10-15')
    def test_current_calendar__start_and_past_end(self):
        self.employee.calendar_ids = [
            (0, 0, {"date_start": "2024-01-01", "date_end": "2024-09-30", "calendar_id": self.calendar1.id}),
        ]
        self.assertTrue(self.employee.resource_calendar_id)
        self.assertFalse(self.employee.som_current_calendar_id)

        self.employee.calendar_ids = [
            (0, 0, {"date_start": "2024-10-01", "date_end": "2024-10-14", "calendar_id": self.calendar2.id}),
        ]
        self.assertFalse(self.employee.som_current_calendar_id)
