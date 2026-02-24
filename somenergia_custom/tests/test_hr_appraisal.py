# -*- coding: utf-8 -*-
from odoo.tests import tagged, TransactionCase
from odoo.exceptions import ValidationError, AccessError
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged('appraisal_state_restriction')
class TestHrAppraisalStateRestriction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.department = cls.env['hr.department'].create({
            'name': 'Test Department',
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'department_id': cls.department.id,
        })

        cls.employee_colleague = cls.env['hr.employee'].create({
            'name': 'Test Employee Colleague',
            'department_id': cls.department.id,
        })

        cls.stage_initial = cls.env['hr.appraisal.stages'].search([('sequence', '=', 0)], limit=1)
        if not cls.stage_initial:
            cls.stage_initial = cls.env['hr.appraisal.stages'].create({
                'name': 'Initial',
                'sequence': 0,
            })

        cls.stage_draft = cls.env['hr.appraisal.stages'].search([('sequence', '=', 1)], limit=1)
        if not cls.stage_draft:
            cls.stage_draft = cls.env['hr.appraisal.stages'].create({
                'name': 'Draft',
                'sequence': 1,
            })

        cls.stage_sent = cls.env['hr.appraisal.stages'].search([('sequence', '=', 2)], limit=1)
        if not cls.stage_sent:
            cls.stage_sent = cls.env['hr.appraisal.stages'].create({
                'name': 'Sent',
                'sequence': 2,
            })

        # create survey template to avoid validation error when starting appraisal
        cls.survey_id = cls.env['survey.survey'].create({
            'title': 'Test Survey',
        })

        cls.appraisal = cls.env['hr.appraisal'].with_context(DISABLED_MAIL_CONTEXT).create({
            'emp_id': cls.employee.id,
            'som_type': 'generic',
            'state': cls.stage_initial.id,
            'appraisal_date': '2026-02-01',
            'appraisal_deadline': '2026-02-28',
        })

    def test_cannot_change_state_directly(self):
        """Test that state cannot be changed directly without appraisal_action context"""
        with self.assertRaises(ValidationError) as cm:
            self.appraisal.write({'state': self.stage_draft.id})
        self.assertIn('cannot change the state', str(cm.exception).lower())

    def test_cannot_change_state_from_form_view(self):
        """Test that state cannot be changed from form view"""
        with self.assertRaises(ValidationError):
            self.appraisal.state = self.stage_draft.id

    def test_can_change_state_with_context(self):
        """Test that state can be changed with appraisal_action context"""
        self.appraisal.with_context(appraisal_action=True).write({
            'state': self.stage_draft.id
        })
        self.assertEqual(self.appraisal.state.id, self.stage_draft.id)

    def test_action_initialize_appraisal(self):
        """Test that action_initialize_appraisal changes state properly"""
        self.appraisal.action_initialize_appraisal()
        self.assertEqual(self.appraisal.state.id, self.stage_draft.id)
        self.assertFalse(self.appraisal.check_initial)
        self.assertTrue(self.appraisal.check_draft)

    def test_action_start_appraisal_changes_state(self):
        """Test that action_start_appraisal changes state properly"""
        # First move to draft state
        self.appraisal.with_context(appraisal_action=True).write({
            'state': self.stage_draft.id,
        })

        # # We add reviewers to ensure that the appraisal can be started, as it requires at least one reviewer
        # self.appraisal.reviewer_ids = [(0, 0, {
        #     'employee_id': self.employee.id,
        # })]

        # Try to start appraisal and check raises error if no reviewers
        with self.assertRaises(ValidationError):
            self.appraisal.action_start_appraisal()

        # Now add a reviewer and start appraisal
        self.appraisal.write({
            'hr_emp': True,
            'emp_survey_id': self.survey_id.id,
            'hr_colleague': True,
            'hr_colleague_ids': [
                (6, 0, [self.employee.id, self.employee_colleague.id]),
            ],
            'colleague_survey_id': self.survey_id.id,
        })
        self.appraisal.action_start_appraisal()

        self.assertEqual(self.appraisal.state.id, self.stage_sent.id)
        self.assertTrue(self.appraisal.check_sent)
        self.assertFalse(self.appraisal.check_draft)
        self.assertFalse(self.appraisal.check_initial)

    def test_cannot_write_other_fields_with_state(self):
        """Test that trying to write state along with other fields also fails"""
        with self.assertRaises(ValidationError):
            self.appraisal.write({
                'state': self.stage_draft.id,
                'final_evaluation': '<p>Test evaluation</p>',
            })

    def test_can_write_other_fields_without_state(self):
        """Test that other fields can be written without state"""
        self.appraisal.write({
            'final_evaluation': '<p>Test evaluation</p>',
        })
        self.assertEqual(self.appraisal.final_evaluation, '<p>Test evaluation</p>')


@tagged('appraisal_security_rules')
class TestHrAppraisalSecurityRules(TransactionCase):
    """Test security rules for appraisal access based on department"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create departments
        cls.dept_sales = cls.env['hr.department'].create({
            'name': 'Sales Department',
        })

        cls.dept_hr = cls.env['hr.department'].create({
            'name': 'HR Department',
        })

        # Create employees in different departments
        cls.employee_sales_1 = cls.env['hr.employee'].create({
            'name': 'Sales Employee 1',
            'department_id': cls.dept_sales.id,
        })

        cls.employee_sales_2 = cls.env['hr.employee'].create({
            'name': 'Sales Employee 2',
            'department_id': cls.dept_sales.id,
        })

        cls.employee_hr = cls.env['hr.employee'].create({
            'name': 'HR Employee',
            'department_id': cls.dept_hr.id,
        })

        # Get or create the Team Leader group
        cls.group_team_leader = cls.env.ref('oh_appraisal.group_appraisal_employee')

        # Create users with Team Leader role
        cls.user_sales_team_leader = cls.env['res.users'].create({
            'name': 'Sales Team Leader',
            'login': 'sales_leader',
            'email': 'sales_leader@example.com',
            'password': 'password123',
            'groups_id': [(4, cls.group_team_leader.id)],
            'company_id': cls.employee_sales_1.company_id.id,
            'company_ids': [(6, 0, [cls.employee_sales_1.company_id.id])],
        })

        cls.user_hr_team_leader = cls.env['res.users'].create({
            'name': 'HR Team Leader',
            'login': 'hr_leader',
            'email': 'hr_leader@example.com',
            'password': 'password123',
            'groups_id': [(4, cls.group_team_leader.id)],
            'company_id': cls.employee_hr.company_id.id,
            'company_ids': [(6, 0, [cls.employee_hr.company_id.id])],
        })

        cls.employee_sales_1.write({'user_id': cls.user_sales_team_leader.id})
        cls.employee_hr.write({'user_id': cls.user_hr_team_leader.id})

        if 'department_id' in cls.user_sales_team_leader._fields:
            cls.user_sales_team_leader.write({'department_id': cls.dept_sales.id})

        if 'department_id' in cls.user_hr_team_leader._fields:
            cls.user_hr_team_leader.write({'department_id': cls.dept_hr.id})

        # Create survey template
        cls.survey_id = cls.env['survey.survey'].create({
            'title': 'Test Survey',
        })

        # Get the initial stage
        cls.stage_initial = cls.env['hr.appraisal.stages'].search([('sequence', '=', 0)], limit=1)
        if not cls.stage_initial:
            cls.stage_initial = cls.env['hr.appraisal.stages'].create({
                'name': 'Initial',
                'sequence': 0,
            })

        # Create appraisals for different employees
        cls.appraisal_sales_1 = cls.env['hr.appraisal'].with_context(DISABLED_MAIL_CONTEXT).create({
            'emp_id': cls.employee_sales_1.id,
            'som_type': 'generic',
            'state': cls.stage_initial.id,
            'appraisal_date': '2026-02-01',
            'appraisal_deadline': '2026-02-28',
        })

        cls.appraisal_sales_2 = cls.env['hr.appraisal'].with_context(DISABLED_MAIL_CONTEXT).create({
            'emp_id': cls.employee_sales_2.id,
            'som_type': 'generic',
            'state': cls.stage_initial.id,
            'appraisal_date': '2026-02-01',
            'appraisal_deadline': '2026-02-28',
        })

        cls.appraisal_hr = cls.env['hr.appraisal'].with_context(DISABLED_MAIL_CONTEXT).create({
            'emp_id': cls.employee_hr.id,
            'som_type': 'generic',
            'state': cls.stage_initial.id,
            'appraisal_date': '2026-02-01',
            'appraisal_deadline': '2026-02-28',
        })

    def test_team_leader_can_see_appraisals_same_department(self):
        """Test that a Team Leader can see appraisals of employees in their department"""
        # Sales team leader should see appraisals from sales employees
        appraisals = self.env['hr.appraisal'].with_user(self.user_sales_team_leader).search([])
        appraisal_ids = appraisals.mapped('id')

        # Should see both sales appraisals
        self.assertIn(self.appraisal_sales_1.id, appraisal_ids,
                      "Team Leader should see appraisals from their department")
        self.assertIn(self.appraisal_sales_2.id, appraisal_ids,
                      "Team Leader should see all appraisals from their department")

    def test_team_leader_cannot_see_appraisals_different_department(self):
        """Test that a Team Leader cannot see appraisals of employees in other departments"""
        # Sales team leader should NOT see HR appraisals
        appraisals = self.env['hr.appraisal'].with_user(self.user_sales_team_leader).search([])
        appraisal_ids = appraisals.mapped('id')

        self.assertNotIn(self.appraisal_hr.id, appraisal_ids,
                         "Team Leader should NOT see appraisals from other departments")

    def test_team_leader_can_write_same_department_appraisal(self):
        """Test that a Team Leader can write appraisals from their department"""
        appraisal = self.appraisal_sales_1.with_user(self.user_sales_team_leader)

        # Should not raise an error
        try:
            appraisal.write({'final_evaluation': '<p>Test evaluation</p>'})
            success = True
        except AccessError:
            success = False

        self.assertTrue(
            success, "Team Leader should be able to write appraisals from their department")

    def test_team_leader_cannot_write_different_department_appraisal(self):
        """Test that a Team Leader cannot write appraisals from other departments"""
        appraisal = self.appraisal_hr.with_user(self.user_sales_team_leader)

        with self.assertRaises(AccessError):
            appraisal.write({'final_evaluation': '<p>Test evaluation</p>'})

    def test_different_team_leaders_isolated(self):
        """Test that different Team Leaders only see their own department appraisals"""
        # Sales team leader views
        sales_appraisals = self.env['hr.appraisal'].with_user(
            self.user_sales_team_leader).search([])
        sales_ids = sales_appraisals.mapped('id')

        # HR team leader views
        hr_appraisals = self.env['hr.appraisal'].with_user(
            self.user_hr_team_leader).search([])
        hr_ids = hr_appraisals.mapped('id')

        # Sales leader should see sales appraisals
        self.assertIn(self.appraisal_sales_1.id, sales_ids)
        self.assertIn(self.appraisal_sales_2.id, sales_ids)

        # HR leader should see HR appraisals
        self.assertIn(self.appraisal_hr.id, hr_ids)

        # Sales leader should NOT see HR appraisals
        self.assertNotIn(self.appraisal_hr.id, sales_ids)

        # HR leader should NOT see sales appraisals
        self.assertNotIn(self.appraisal_sales_1.id, hr_ids)
        self.assertNotIn(self.appraisal_sales_2.id, hr_ids)

    def test_team_leader_rule_domain_force(self):
        """Test that the Team Leader rule is applied with the expected domain"""
        rule = self.env.ref('oh_appraisal.hr_appraisal_rule')
        self.assertEqual(
            rule.domain_force,
            "[('emp_id.department_id','=',user.department_id.id)]",
            "Team Leader appraisal rule should keep the expected domain_force",
        )
        group_ids = rule.groups.mapped('id')
        self.assertIn(
            self.group_team_leader.id,
            group_ids,
            "Team Leader appraisal rule should apply to Team Leader group",
        )
