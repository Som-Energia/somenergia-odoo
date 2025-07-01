from odoo import http
from odoo.http import request
from odoo.addons.survey.controllers.main import Survey


class CustomSurvey(Survey):

    @http.route()
    def survey_start(self, survey_token, answer_token=None, email=False, **post):
        remote_ip = request.httprequest.remote_addr
        res = super(CustomSurvey, self).survey_start(survey_token, answer_token=answer_token, email=email, **post)
        return res

    @http.route()
    def survey_submit(self, survey_token, answer_token, **post):
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)

        if access_data['validity_code'] is not True:
            return {'error': access_data['validity_code']}
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        if answer_sudo.state == 'done':
            return {'error': 'unauthorized'}

        if post.get('previous_page_id', False):
            # page back
            questions, page_or_question_id = survey_sudo._get_survey_questions(answer=answer_sudo,
                                                                               page_id=post.get('page_id'),
                                                                               question_id=post.get('question_id'))
            q_ids = questions.filtered(
                lambda x: x.question_type in ['simple_choice', 'multiple_choice'] and x.constr_mandatory
            )
            q_ids.write({'constr_mandatory': False})
            res = super(CustomSurvey, self).survey_submit(survey_token, answer_token, **post)
            q_ids.write({'constr_mandatory': True})
        else:
            # page next
            if not answer_sudo.som_remote_ip:
                try:
                    answer_sudo.som_remote_ip = request.httprequest.remote_addr
                except Exception as e:
                    answer_sudo.som_remote_ip = "-"
            res = super(CustomSurvey, self).survey_submit(survey_token, answer_token, **post)

        return res
