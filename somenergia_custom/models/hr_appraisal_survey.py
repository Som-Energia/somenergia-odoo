# -- coding: utf-8 --
from odoo import models, fields, api, _


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    def som_action_send_collaboration_reminder(self):
        tmpl_reminder_id = self.env.ref('somenergia_custom.som_email_template_feedback_remind_collaborator')
        for record in self.filtered(lambda x: x.appraisal_id and x.appraisal_id.som_type == 'annual_360'):
            tmpl_reminder_id.send_mail(record.id, force_send=True)
