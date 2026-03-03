# -*- coding: utf-8 -*-
from odoo import fields
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

        # Create project area for the department
        cls.project_area = cls.env['project.project'].create({
            'name': 'Test Project Area',
        })
        cls.department.som_project_area_id = cls.project_area.id

        # Create employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'department_id': cls.department.id,
        })

        # Create projects
        cls.project_main = cls.env['project.project'].create({
            'name': 'Main Project',
        })
        cls.project_transversal = cls.env['project.project'].create({
            'name': 'Transversal Project',
        })

        # Create task
        cls.task = cls.env['project.task'].create({
            'name': 'Test Task',
            'project_id': cls.project_main.id,
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

    def test_create_timesheet_sets_project_from_department_area(self):
        """Test that project_id is set from employee's department project area"""
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        self.assertEqual(
            timesheet.project_id.id,
            self.project_area.id,
            "project_id should be set from employee's department project area"
        )

    def test_create_timesheet_with_additional_project(self):
        """Test creating timesheet with som_additional_project_id creates linked timesheet"""
        # Set additional project on task
        self.task.write({'som_additional_project_id': self.project_transversal.id})

        timesheet_ids = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        self.assertEqual(
            len(timesheet_ids),
            2,
            "Creating timesheet with som_additional_project_id should create 2 timesheets"
        )

        timesheets_project_area_id = timesheet_ids.filtered(
            lambda x: x.project_id.id == self.department.som_project_area_id.id)

        self.assertTrue(
            timesheets_project_area_id,
            "One of the timesheets should be linked to the department's project area"
        )
        self.assertEqual(
            timesheets_project_area_id.project_id.id,
            self.department.som_project_area_id.id,
            "One of the timesheets should be linked to the department's project area"
        )
        self.assertEqual(
            timesheets_project_area_id.som_additional_project_id.id,
            self.project_transversal.id,
            "The timesheet linked to the project area should have "
            "the transversal project as additional project"
        )

        timesheet_additional_id = timesheet_ids.filtered(
            lambda x: x.project_id.id == self.project_transversal.id)

        self.assertTrue(
            timesheet_additional_id,
            "One of the timesheets should be linked to the transversal project"
        )
        self.assertEqual(
            timesheet_additional_id.project_id.id,
            self.project_transversal.id,
            "One of the timesheets should be linked to the transversal project"
        )

        self.assertEqual(
            timesheet_additional_id.unit_amount,
            2.0,
            "The timesheet linked to the transversal project should have "
            "the same hours as the main timesheet"
        )

        # # Verify UUID hook is set
        self.assertTrue(
            timesheets_project_area_id.som_timesheet_uuid_hook,
            "UUID hook should be set on the timesheet linked to the project area"
        )

        self.assertTrue(
            timesheet_additional_id.som_timesheet_uuid_hook,
            "UUID hook should be set on the timesheet linked to the transversal project"
        )

        self.assertEqual(
            timesheets_project_area_id.som_timesheet_uuid_hook,
            timesheet_additional_id.som_timesheet_uuid_hook,
            "Both timesheets should share the same UUID hook"
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

    def test_write_timesheet_updates_linked_hours(self):
        """Test that updating hours also updates linked timesheet"""
        # Set additional project on task
        self.task.som_additional_project_id = self.project_transversal.id

        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        linked_timesheet = timesheet.som_timesheet_add_id

        # Update hours
        timesheet.write({
            'unit_amount': 5.0,
        })

        self.assertEqual(
            linked_timesheet.unit_amount,
            5.0,
            "Linked timesheet hours should be updated"
        )

    def test_write_add_additional_project_creates_link(self):
        """Test adding som_additional_project_id creates linked timesheet"""
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        self.assertFalse(
            timesheet.som_timesheet_add_id,
            "No linked timesheet should exist initially"
        )

        # Add additional project
        timesheet.write({
            'som_additional_project_id': self.project_transversal.id,
        })

        self.assertTrue(
            timesheet.som_timesheet_add_id,
            "Linked timesheet should be created"
        )
        self.assertEqual(
            timesheet.som_timesheet_add_id.project_id.id,
            self.project_transversal.id,
            "Linked timesheet should have the transversal project"
        )

    def test_write_change_additional_project_updates_link(self):
        """Test changing som_additional_project_id updates linked timesheet project"""
        # Create another transversal project
        project_transversal_2 = self.env['project.project'].create({
            'name': 'Transversal Project 2',
        })

        # Set additional project on task
        self.task.som_additional_project_id = self.project_transversal.id

        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        linked_timesheet = timesheet.som_timesheet_add_id

        # Change additional project
        timesheet.write({
            'som_additional_project_id': project_transversal_2.id,
        })

        self.assertEqual(
            linked_timesheet.project_id.id,
            project_transversal_2.id,
            "Linked timesheet project should be updated"
        )

    def test_write_remove_additional_project_deletes_link(self):
        """Test removing som_additional_project_id deletes linked timesheet"""
        # Set additional project on task
        self.task.som_additional_project_id = self.project_transversal.id

        timesheet_ids = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })

        timesheets_project_area_id = timesheet_ids.filtered(
            lambda x: x.project_id.id == self.department.som_project_area_id.id)

        timesheet_additional_id = timesheet_ids.filtered(
            lambda x: x.project_id.id == self.project_transversal.id)

        id_additional_tsh = timesheet_additional_id.id

        # Remove additional project
        timesheets_project_area_id.write({
            'som_additional_project_id': False,
        })

        # Check linked timesheet is deleted
        deleted = self.env['account.analytic.line'].with_context(active_test=False).search([
            ('id', '=', id_additional_tsh),
        ])
        self.assertFalse(
            deleted,
            "Linked timesheet should be deleted"
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

    def test_write_task_change_additional_project_not_allowed(self):
        """
        Test that changing task's som_additional_project_id is not allowed
        when it has timesheets linked
        """
        # Set additional project on task
        self.task.som_additional_project_id = self.project_transversal.id
        timesheet_ids = self.env['account.analytic.line'].create({
            'name': 'Test Timesheet',
            'task_id': self.task.id,
            'project_id': self.project_main.id,
            'employee_id': self.employee.id,
            'date_time': self.test_date,
            'unit_amount': 2.0,
        })
        # Try to change additional project
        with self.assertRaises(Exception):
            self.task.write({
                'som_additional_project_id': False,
            })

    def test_write_task_change_additional_project_allowed(self):
        """
        Test that changing task's som_additional_project_id is allowed
        """
        # Set additional project on task
        self.task.som_additional_project_id = self.project_transversal.id
        self.task.write({
            'som_additional_project_id': False,
        })
        self.assertFalse(
            self.task.som_additional_project_id,
            "som_additional_project_id should be removed successfully after unlinking timesheets"
        )
