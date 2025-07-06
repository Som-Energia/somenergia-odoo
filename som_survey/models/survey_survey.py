# -- coding: utf-8 --
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError

class Survey(models.Model):
    _inherit = "survey.survey"

    user_input_ids = fields.One2many(
        'survey.user_input', 'survey_id',
        groups='survey.group_survey_user,som_survey.som_group_survey_public_manager',
    )

    def _ensure_survey_group_user(self, user):
        group_survey_user_id = self.env.ref('survey.group_survey_user')
        flag_remove_group = False
        if not user.has_group('survey.group_survey_user') and user.has_group(
                'som_survey.som_group_survey_public_manager'):
            # add the group to the user temporally to avoid restriction
            user.sudo().write({'groups_id': [(4, group_survey_user_id.id)]})
            flag_remove_group = True
        return group_survey_user_id, flag_remove_group

    def _create_answer(self, user=False, partner=False, email=False, test_entry=False, check_attempts=True, **additional_vals):
        """
        We do this to avoid '_check_answer_creation' that
        just allow 'survey.group_survey_user' users to create a test survey
        """
        group_survey_user_id, flag_remove_group = self._ensure_survey_group_user(user)

        user_inputs = super()._create_answer(user=user, partner=partner, email=email, test_entry=test_entry, check_attempts=check_attempts, **additional_vals)

        if flag_remove_group:
            # remove the group added to the user temporally
            user.sudo().write({'groups_id': [(3, group_survey_user_id.id)]})

        return user_inputs

    def action_start_session(self):
        group_survey_user_id, flag_remove_group = self._ensure_survey_group_user(self.env.user)

        res = super().action_start_session()

        if flag_remove_group:
            # remove the group added to the user temporally
            self.env.user.sudo().write({'groups_id': [(3, group_survey_user_id.id)]})

        return res

    def action_end_session(self):
        group_survey_user_id, flag_remove_group = self._ensure_survey_group_user(self.env.user)

        res = super().action_end_session()

        if flag_remove_group:
            # remove the group added to the user temporally
            self.env.user.sudo().write({'groups_id': [(3, group_survey_user_id.id)]})

        return res
