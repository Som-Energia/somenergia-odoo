# -*- coding: utf-8 -*-
from odoo.tests import tagged, TransactionCase
from odoo.exceptions import ValidationError
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
