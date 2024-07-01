# -*- coding:utf-8 -*-
import logging

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class HrAppraisal(models.Model):
    _inherit = "hr.appraisal"

    @api.depends('som_answer_ids', 'som_answer_ids.state')
    def _compute_received_all_answers(self):
        for record in self.filtered(lambda x: x.tot_sent_survey):
            count_completed = len(record.som_answer_ids.filtered(lambda x: x.state == 'done'))
            record.som_got_all_answers = (count_completed == record.tot_sent_survey)
            if record.som_got_all_answers:
                record.som_got_all_answers_date = fields.Date.today()

    tot_sent_survey = fields.Integer(copy=False)
    final_evaluation = fields.Html(string="Final Evaluation")

    som_type = fields.Selection(
        selection=[
            ("annual_360", "Feedback annual 360"),
            ("generic", "Feedback generic"),
        ],
        string="Type",
        required=True,
    )

    som_answer_ids = fields.One2many(
        string="Answers",
        comodel_name="survey.user_input",
        inverse_name="appraisal_id",
    )

    som_got_all_answers = fields.Boolean(
        string="Received all answers",
        default=False,
        compute="_compute_received_all_answers",
        copy=False,
        store=True,
    )

    som_got_all_answers_date = fields.Date(
        string="Date received all answers",
        compute="_compute_received_all_answers",
        copy=False,
        store=True,
    )

    som_warned_all_answers = fields.Boolean(
        string="Warned all answers",
        default=False,
        copy=False
    )

    @api.model
    def get_mail_entorn_laboral(self):
        return self.env["ir.config_parameter"].sudo().get_param("som_mail_entorn_laboral")

    def action_initialize_appraisal(self):
        super().action_initialize_appraisal()
        tmpl_id = self.env.ref('somenergia_custom.som_email_template_feedback_initialize')
        for record in self.filtered(lambda x: x.som_type == 'annual_360'):
            tmpl_id.send_mail(record.id, force_send=True)

    def action_start_appraisal(self):
        """This function will start the appraisal by sending emails to the corresponding employees
        specified in the appraisal"""
        self.ensure_one()
        tmpl_generic_id = self.env.ref('somenergia_custom.som_email_template_feedback_generic')
        tmpl_empl_id = self.env.ref('somenergia_custom.som_email_template_feedback_start_employee')
        tmpl_col_id = self.env.ref('somenergia_custom.som_email_template_feedback_start_collaborator')

        send_count = 0
        appraisal_reviewers_list = self.fetch_appraisal_reviewer()
        for appraisal_reviewers, survey_id in appraisal_reviewers_list:
            if len(appraisal_reviewers) == 1 and appraisal_reviewers == self.emp_id:
                continue
            for reviewers in appraisal_reviewers:
                response = survey_id._create_answer(
                    survey_id=survey_id.id,
                    deadline=self.appraisal_deadline,
                    partner=reviewers.user_id.partner_id,
                    email=reviewers.work_email,
                    appraisal_id=self.ids[0],
                )
                template_to_send_id = tmpl_col_id if self.som_type == 'annual_360' else tmpl_generic_id
                template_to_send_id.send_mail(response.id, force_send=True)
                send_count += 1

        if self.hr_emp and self.emp_survey_id:
            self.ensure_one()
            if not self.response_id:
                response = self.emp_survey_id._create_answer(
                    survey_id=self.emp_survey_id.id,
                    deadline=self.appraisal_deadline,
                    partner_id=self.emp_id.user_id.partner_id.id,
                    email=self.emp_id.work_email,
                    appraisal_id=self.ids[0],
                )
                self.response_id = response.id
            else:
                response = self.response_id
            template_to_send_id = tmpl_empl_id if self.som_type == 'annual_360' else tmpl_generic_id
            template_to_send_id.send_mail(response.id, force_send=True)
            send_count += 1

        self.write({"tot_sent_survey": send_count})
        rec = self.env["hr.appraisal.stages"].search([("sequence", "=", 2)])
        self.state = rec.id
        self.check_sent = True
        self.check_draft = False
        self.check_initial = False

    def action_get_answers(self):
        res = super().action_get_answers()
        if res.get("domain", False):
            res["domain"] = [("appraisal_id", "=", self.ids[0])]
        return res

    @api.model
    def do_process_all_answers_received(self):
        tmpl_id = self.env.ref('somenergia_custom.som_email_template_feedback_received_all_answers')
        app_ids = self.env['hr.appraisal'].search([
            ('som_got_all_answers', '=', True),
            ('som_warned_all_answers', '=', False),
        ])
        for app_id in app_ids:
            tmpl_id.send_mail(app_id.id, force_send=True)
            app_id.som_warned_all_answers = True

    @api.model
    def send_mail_feedback_reminder(self):
        from_date = datetime(datetime.today().year, datetime.today().month, 1) + relativedelta(months=1)
        to_date = from_date + relativedelta(months=1) - relativedelta(days=1)
        app_ids = self.env['hr.appraisal'].search([
            ('appraisal_date', '>=', fields.Date.to_string(from_date)),
            ('appraisal_date', '<=', fields.Date.to_string(to_date)),
        ], order="appraisal_date asc")

        str_app = ''
        for app_id in app_ids:
            str_date = app_id.appraisal_date.strftime('%d/%m/%Y')
            str_app += f'Feedback Id {str(app_id.id)} | {app_id.emp_id.name} | {str_date} <br/>'

        somadmin_user_id = self.env.ref('base.somadmin')
        try:
            mail_html = _("""
                        <div style="margin: 0px; padding: 0px;">
                            <p style="margin: 0px; padding: 0px; font-size: 13px;">
                                Hola,
                                <br/><br/>
                                Aquests són els %s feedbacks del mes vinent:
                                <br/><br/>
                                %s
                                <br/><br/>
                                <a t-att-href="object.signup_url" style="background-color:#875A7B; padding:8px 16px 8px 16px; text-decoration:none; color:#fff; border-radius:5px" href="https://odoo.somenergia.coop/web#action=509&model=hr.appraisal&view_type=list&menu_id=366" target="_blank" class="btn btn-primary">Veure Feedbacks</a>
                                <br/><br/>
                                Salut!
                            </p>
                        </div>
                    """) % (
                len(app_ids), str_app,
            )

            mail_values = {
                'author_id': somadmin_user_id.partner_id.id,
                'body_html': mail_html,
                'subject': _('Odoo Som - Recordatori Feedbacks mes vinent %s') % datetime.now().strftime('%d/%m/%Y'),
                'email_from':
                    somadmin_user_id.email_formatted or somadmin_user_id.company_id.catchall or
                    somadmin_user_id.company_id.email,
                'email_to': self.get_mail_entorn_laboral(),
                'auto_delete': False,
            }

            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()

        except Exception as e:
            _logger.exception("Worked weeks reminder - Unable to send email.")
