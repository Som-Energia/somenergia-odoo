# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged, TransactionCase
from datetime import datetime, timedelta


@tagged('som_analytic_account_line')
class TestAnalyticAccountLine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a department
        cls.department = cls.env['hr.department'].create({
            'name': 'Test Department',
        })

        # Create service project used by task timesheets
        cls.project_service = cls.env['project.project'].create({
            'name': 'Test Service Project',
        })

        # Create employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'department_id': cls.department.id,
        })

        # Create projects
        cls.project_main = cls.env['project.project'].create({
            'name': 'Main Project',
        })

        # Create task
        cls.task = cls.env['project.task'].create({
            'name': 'Test Task',
            'project_id': cls.project_main.id,
            'som_project_id': cls.project_service.id,
        })

        # Create a calendar week
        test_date = datetime(2022, 3, 7, 12, 0, 0)  # Monday, March 7, 2022
        cls.calendar_week = cls.env['som.calendar.week'].create({
            'name': '2022-W10',
            'som_cw_code': '2022W10',
            'som_cw_date': test_date,
            'som_cw_date_end': test_date + timedelta(days=6),
            'som_cw_week_number': 10,
            'som_cw_week_year': 2022,
            'som_cw_year': 2022,
        })

        cls.worked_week = cls.env['som.worked.week'].create({
            'name': 'Worked Week 2022-W10',
            'som_week_id': cls.calendar_week.id,
            'som_employee_id': cls.employee.id,
        })

        cls.test_date = test_date

    def test_create_timesheet_auto_fills_week_from_date(self):
        """Test that som_week_id is automatically filled based on date_time"""
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        self.assertEqual(
            timesheet.som_week_id.id,
            self.calendar_week.id,
            "som_week_id should be automatically filled based on date_time"
        )

        self.assertEqual(
            timesheet.som_worked_week_id.id,
            self.worked_week.id,
            "som_worked_week_id should be automatically filled based on date_time and employee"
        )

    def test_create_timesheet_uses_existing_worked_week(self):
        """Test that existing som_worked_week_id is reused"""
        # Create first timesheet (creates worked_week)
        timesheet1 = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet 1',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        worked_week_id = timesheet1.som_worked_week_id.id

        # Create second timesheet (should reuse worked_week)
        timesheet2 = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet 2',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date + timedelta(days=1),
            'unit_amount': 3.0,
        })

        self.assertEqual(
            timesheet2.som_worked_week_id.id,
            worked_week_id,
            "Both timesheets in same week should share the same worked_week"
        )

    def test_create_timesheet_sets_project_from_task_service_project(self):
        """Test that project_id is set from the task service project."""
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        self.assertEqual(
            timesheet.project_id.id,
            self.project_service.id,
            "project_id should be set from the task service project"
        )

    def test_create_timesheet_overrides_incoming_project_with_task_service_project(self):
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        self.assertEqual(
            timesheet.project_id.id,
            self.project_service.id,
            "task service project should take precedence over the provided project_id"
        )

    def test_create_timesheet_without_task_service_project_keeps_given_project(self):
        self.task.som_project_id = False

        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        self.assertEqual(
            timesheet.project_id.id,
            self.project_main.id,
            "Timesheets should keep the provided project when the task has no service project"
        )

    def test_write_timesheet_updates_week_when_date_changes(self):
        """Test that changing date_time updates som_week_id and som_worked_week_id"""
        # Create initial timesheet
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        # Create another calendar week for next week
        next_week_date = self.test_date + timedelta(days=7)  # Monday, March 14, 2022
        next_calendar_week = self.env['som.calendar.week'].create({
            'name': '2022-W11',
            'som_cw_code': '2022W11',
            'som_cw_date': next_week_date,
            'som_cw_date_end': next_week_date + timedelta(days=6),
            'som_cw_week_number': 11,
            'som_cw_week_year': 2022,
            'som_cw_year': 2022,
        })

        # Create another worked week for the same next week
        self.env['som.worked.week'].create({
            'name': 'Worked Week 2022-W11',
            'som_week_id': next_calendar_week.id,
            'som_employee_id': self.employee.id,
        })

        initial_week_id = timesheet.som_week_id.id
        initial_worked_week_id = timesheet.som_worked_week_id.id

        # Update timesheet date to next week
        timesheet.write({
            'date_time': next_week_date,
        })

        self.assertEqual(
            timesheet.som_week_id.id,
            next_calendar_week.id,
            "som_week_id should be updated to new week"
        )

        self.assertNotEqual(
            timesheet.som_worked_week_id.id,
            initial_worked_week_id,
            "som_worked_week_id should be updated to new worked week"
        )

        self.assertEqual(
            timesheet.som_worked_week_id.som_week_id.id,
            next_calendar_week.id,
            "som_worked_week_id should be updated to new week"
        )

        self.assertNotEqual(
            timesheet.som_worked_week_id.id,
            initial_worked_week_id,
            "som_worked_week_id should be updated to new worked week"
        )

    def test_create_without_task_doesnt_auto_fill(self):
        """Test that timesheets without task_id doesn't auto-fill week fields"""
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet Direct',
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date': fields.Date.today(),
            'unit_amount': 2.0,
        })

        # Without task_id, the auto-fill logic shouldn't trigger
        self.assertFalse(
            timesheet.som_week_id,
            "som_week_id should not be auto-filled without task_id"
        )
        self.assertFalse(
            timesheet.som_worked_week_id,
            "som_worked_week_id should not be auto-filled without task_id"
        )

    def test_write_change_employee_doesnt_change_week(self):
        """Test that changing employee_id doesn't change som_week_id"""
        # Create another employee
        employee_2 = self.env['hr.employee'].create({
            'name': 'Test Employee 2',
            'department_id': self.department.id,
        })

        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        initial_week_id = timesheet.som_week_id.id

        # Change employee
        timesheet.write({
            'employee_id': employee_2.id,
        })

        self.assertEqual(
            timesheet.som_week_id.id,
            initial_week_id,
            "som_week_id should not change when changing employee"
        )

    def test_write_change_employee_change_worked_week(self):
        """
        Test that changing employee_id changes som_worked_week_id to the one of the new employee
        """
        # Create another employee
        employee_2 = self.env['hr.employee'].create({
            'name': 'Test Employee 2',
            'department_id': self.department.id,
        })

        # Create a worked week for the second employee
        worked_week_2 = self.env['som.worked.week'].create({
            'name': 'Worked Week Employee 2',
            'som_week_id': self.calendar_week.id,
            'som_employee_id': employee_2.id,
        })

        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        # Change employee
        timesheet.write({
            'employee_id': employee_2.id,
        })

        self.assertEqual(
            timesheet.som_worked_week_id.id,
            worked_week_2.id,
            "som_worked_week_id should change to the one of the new employee"
        )

    def test_create_without_task_keeps_explicit_project(self):
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet Direct',
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date': fields.Date.today(),
            'unit_amount': 2.0,
        })

        self.assertEqual(
            timesheet.project_id.id,
            self.project_main.id,
            "Timesheets without task_id should keep the provided project"
        )

    def test_write_task_service_project_allowed_without_timesheets(self):
        new_service_project = self.env['project.project'].create({
            'name': 'New Service Project',
        })

        self.task.write({
            'som_project_id': new_service_project.id,
        })

        self.assertEqual(
            self.task.som_project_id.id,
            new_service_project.id,
            "som_project_id should be updated when there are no linked timesheets"
        )

    def test_write_task_service_project_allowed_when_timesheets_use_other_project(self):
        other_service_project = self.env['project.project'].create({
            'name': 'Other Service Project',
        })
        new_service_project = self.env['project.project'].create({
            'name': 'Replacement Service Project',
        })

        timesheet = self.env['account.analytic.line'].create({
            'name': 'Manual Timesheet',
            'task_id': self.task.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })
        timesheet.write({'project_id': other_service_project.id})

        self.task.write({
            'som_project_id': new_service_project.id,
        })

        self.assertEqual(
            self.task.som_project_id.id,
            new_service_project.id,
            "som_project_id should be updated when existing timesheets use another project"
        )

    def test_write_task_service_project_blocked_with_linked_timesheets(self):
        new_service_project = self.env['project.project'].create({
            'name': 'Blocked Service Project',
        })

        self.env['account.analytic.line'].create({
            'name': 'Service Timesheet',
            'task_id': self.task.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        with self.assertRaises(ValidationError):
            self.task.write({
                'som_project_id': new_service_project.id,
            })

    def test_write_task_service_project_same_value_is_allowed(self):
        self.env['account.analytic.line'].create({
            'name': 'Service Timesheet',
            'task_id': self.task.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        self.task.write({
            'som_project_id': self.project_service.id,
        })

        self.assertEqual(
            self.task.som_project_id.id,
            self.project_service.id,
            "writing the same som_project_id should not be blocked"
        )
