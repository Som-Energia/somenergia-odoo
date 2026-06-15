# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError


@tagged('timesheet_visible_projects')
class TestTimesheetVisibleProjects(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_timesheet_user = cls.env.ref('hr_timesheet.group_hr_timesheet_user')
        cls.group_visible_projects = cls.env.ref(
            'somenergia_custom.som_group_hr_timesheet_visible_projects'
        )

        cls.user_regular = cls._create_user('regular', [cls.group_timesheet_user.id])
        cls.user_visible = cls._create_user('visible', [cls.group_visible_projects.id])
        cls.user_other = cls._create_user('other', [cls.group_timesheet_user.id])

        cls.project_public = cls.env['project.project'].create({
            'name': 'Public Timesheet Project',
            'privacy_visibility': 'employees',
            'allow_timesheets': True,
        })
        cls.project_private = cls.env['project.project'].create({
            'name': 'Private Timesheet Project',
            'privacy_visibility': 'followers',
            'allow_timesheets': True,
        })

        cls.task_public = cls.env['project.task'].create({
            'name': 'Public Task',
            'project_id': cls.project_public.id,
        })
        cls.task_private = cls.env['project.task'].create({
            'name': 'Private Task',
            'project_id': cls.project_private.id,
        })

        cls.line_visible_public = cls._create_timesheet(
            cls.user_visible, cls.task_public, 2.0, 'Visible public work'
        )
        cls.line_other_public = cls._create_timesheet(
            cls.user_other, cls.task_public, 3.0, 'Other public work'
        )
        cls.line_other_private = cls._create_timesheet(
            cls.user_other, cls.task_private, 4.0, 'Other private work'
        )

    @classmethod
    def _create_user(cls, login, group_ids):
        employee = cls.env['hr.employee'].create({
            'name': login.title(),
        })
        user = cls.env['res.users'].create({
            'name': login.title(),
            'login': '%s@example.com' % login,
            'email': '%s@example.com' % login,
            'employee_id': employee.id,
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id] + group_ids)],
        })
        employee.user_id = user.id
        return user

    @classmethod
    def _create_timesheet(cls, user, task, unit_amount, name):
        return cls.env['account.analytic.line'].create({
            'name': name,
            'user_id': user.id,
            'employee_id': user.employee_id.id,
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': unit_amount,
        })

    def test_visible_projects_group_can_read_other_public_timesheets(self):
        lines = self.env['account.analytic.line'].with_user(self.user_visible).search([
            ('id', 'in', [
                self.line_visible_public.id,
                self.line_other_public.id,
                self.line_other_private.id,
            ]),
        ])

        self.assertEqual(
            set(lines.ids),
            {self.line_visible_public.id, self.line_other_public.id},
        )

    def test_regular_timesheet_user_still_sees_only_own_lines(self):
        lines = self.env['account.analytic.line'].with_user(self.user_regular).search([
            ('id', 'in', [
                self.line_visible_public.id,
                self.line_other_public.id,
                self.line_other_private.id,
            ]),
        ])

        self.assertEqual(lines.ids, [])

    def test_visible_projects_group_cannot_write_other_timesheets(self):
        with self.assertRaises(AccessError):
            self.line_other_public.with_user(self.user_visible).write({'name': 'Blocked'})

    def test_visible_projects_group_keeps_own_write_access(self):
        self.line_visible_public.with_user(self.user_visible).write({'name': 'Updated own line'})
        self.assertEqual(self.line_visible_public.name, 'Updated own line')

    def test_visible_projects_group_broadens_analysis_report(self):
        report_lines = self.env['timesheets.analysis.report'].with_user(self.user_visible).search([
            ('project_id', 'in', [self.project_public.id, self.project_private.id]),
        ])

        self.assertEqual(
            set(report_lines.mapped('id')),
            {self.line_visible_public.id, self.line_other_public.id},
        )
