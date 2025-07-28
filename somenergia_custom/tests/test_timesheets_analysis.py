# -*- coding: utf-8 -*-
from odoo import tests
from odoo.tests.common import tagged, TransactionCase
from odoo.exceptions import ValidationError, AccessError


@tagged('timesheets_analysis')
class TestTimesheetsAnalysis(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_user = cls.env.ref('hr_timesheet.group_hr_timesheet_user')
        cls.group_custom = cls.env.ref('somenergia_custom.som_group_hr_timesheet_department')
        cls.group_approver = cls.env.ref('hr_timesheet.group_hr_timesheet_approver')

        Department = cls.env['hr.department'].with_context(tracking_disable=True)

        cls.department_a = Department.create({
            'name': 'Dept A',
        })
        cls.department_b = Department.create({
            'name': 'Dept B',
        })

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan Test',
            'company_id': False,
        })

        # Get the restricted group defined in the module
        cls.group_timesheet_restricted = cls.env.ref('somenergia_custom.som_group_hr_timesheet_department')

        # Create two employees in different departments
        cls.employee_a = cls.env['hr.employee'].create({
            'name': 'Employee A',
            'department_id': cls.department_a.id,
        })
        cls.employee_b = cls.env['hr.employee'].create({
            'name': 'Employee B',
            'department_id': cls.department_b.id,
        })

        # Create User A in Dept A with access group
        cls.user_a = cls.env['res.users'].create({
            'name': 'User A',
            'login': 'usera@example.com',
            'email': 'usera@example.com',
            'employee_id': cls.employee_a.id,
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.group_timesheet_restricted.id
            ])]
        })
        cls.employee_a.write({'user_id': cls.user_a.id})  # Link employee to user

        # Create User B in Dept B without the access group
        cls.user_b = cls.env['res.users'].create({
            'name': 'User B',
            'login': 'userb@example.com',
            'email': 'userb@example.com',
            'employee_id': cls.employee_b.id,
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        cls.employee_b.write({'user_id': cls.user_b.id})

        # Create analytic accounts to assign timesheets to
        cls.account_a = cls.env['account.analytic.account'].create({
            'name': 'Timesheet Project A',
            'plan_id': cls.analytic_plan.id,
        })
        cls.account_b = cls.env['account.analytic.account'].create({
            'name': 'Timesheet Project B',
            'plan_id': cls.analytic_plan.id,
        })

        # Create timesheet entries
        cls.line_user_a = cls.env['account.analytic.line'].create({
            'name': 'Work A',
            'user_id': cls.user_a.id,
            'employee_id': cls.employee_a.id,
            'account_id': cls.account_a.id,
            'unit_amount': 4.0,
        })

        cls.line_user_b = cls.env['account.analytic.line'].create({
            'name': 'Work B',
            'user_id': cls.user_b.id,
            'employee_id': cls.employee_b.id,
            'account_id': cls.account_b.id,
            'unit_amount': 6.0,
        })

    def test_group_exists_and_has_expected_properties(self):
        self.assertTrue(self.group_custom, "Custom group not exists")
        self.assertTrue(self.group_user, "Group hr_timesheet_user not exists")
        self.assertTrue(self.group_approver, "Group group_hr_timesheet_approver not exists")

        self.assertIn(
            self.group_user,
            self.group_custom.implied_ids,
            "'som_group_hr_timesheet_department' should imply 'hr_timesheet_user'"
        )

        self.assertIn(
            self.group_custom,
            self.group_approver.implied_ids,
            "'group_hr_timesheet_approver' should imply 'som_group_hr_timesheet_department'"
        )
