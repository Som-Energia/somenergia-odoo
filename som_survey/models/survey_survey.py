# -- coding: utf-8 --
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError

class Survey(models.Model):
    _inherit = "survey.survey"

    def _create_answer(self, user=False, partner=False, email=False, test_entry=False, check_attempts=True, **additional_vals):
        """
        We do this to avoid '_check_answer_creation' that
        just allow 'survey.group_survey_user' users to create a test survey
        """
        group_survey_user_id = self.env.ref('survey.group_survey_user')
        if not user.has_group('survey.group_survey_user') and user.has_group('som_survey.som_group_survey_public_manager'):
            user.sudo().write({'groups_id': [(4, group_survey_user_id.id)]})

        user_inputs = super()._create_answer(user=user, partner=partner, email=email, test_entry=test_entry, check_attempts=check_attempts, **additional_vals)
        user.sudo().write({'groups_id': [(3, group_survey_user_id.id)]})
        return user_inputs
