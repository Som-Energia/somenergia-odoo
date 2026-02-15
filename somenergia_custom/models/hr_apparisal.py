# -*- coding:utf-8 -*-
import logging

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class HrAppraisal(models.Model):
    _inherit = "hr.appraisal"

    @api.depends('som_answer_ids')
    def _compute_sent_answers(self):
        for record in self:
            record.tot_sent_survey = len(record.som_answer_ids)

    @api.depends('som_answer_ids', 'som_answer_ids.state')
    def _compute_received_all_answers(self):
        for record in self.filtered(lambda x: x.tot_sent_survey):
            count_completed = len(record.som_answer_ids.filtered(lambda x: x.state == 'done'))
            record.som_got_all_answers = (count_completed == record.tot_sent_survey)
            if record.som_got_all_answers:
                record.som_got_all_answers_date = fields.Date.today()

    tot_sent_survey = fields.Integer(
        compute="_compute_sent_answers",
        copy=False,
        store=True,
    )

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

    som_manager_ids = fields.Many2many(
        string='Managers',
        comodel_name='hr.employee',
        related='emp_id.som_manager_ids',
        readonly=True,
    )

    def name_get(self):
        res = []
        for app_id in self:
            name = "[%s] %s" % (str(app_id.appraisal_date), app_id.emp_id.name)
            res += [(app_id.id, name)]
        return res

    @api.model
    def get_mail_entorn_laboral(self):
        return self.env["ir.config_parameter"].sudo().get_param("som_mail_entorn_laboral")

    def action_initialize_appraisal(self):
        stage_initial_id = self.env["hr.appraisal.stages"].search([("sequence", "=", 0)])
        stage_to_start_id = self.env["hr.appraisal.stages"].search([("sequence", "=", 1)])
        tmpl_id = self.env.ref('somenergia_custom.som_email_template_feedback_initialize')
        for record in self.filtered(lambda x: x.state.id == stage_initial_id.id):
            record.with_context(appraisal_action=True).write({
                'state': stage_to_start_id.id,
                'check_initial': False,
                'check_draft': True,
            })
            if record.som_type == 'annual_360':
                tmpl_id.send_mail(record.id, force_send=True)

    def _existing_answer(self, survey_id, employee_id):
        self.ensure_one()
        return len(self.som_answer_ids.filtered(
            lambda x: x.survey_id == survey_id and x.partner_id == employee_id.user_id.partner_id)) > 0

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
            for employee_id in appraisal_reviewers:
                if self._existing_answer(survey_id, employee_id):
                    continue
                response = survey_id._create_answer(
                    survey_id=survey_id.id,
                    deadline=self.appraisal_deadline,
                    partner=employee_id.user_id.partner_id,
                    email=employee_id.work_email,
                    appraisal_id=self.ids[0],
                )
                template_to_send_id = tmpl_col_id if self.som_type == 'annual_360' else tmpl_generic_id
                template_to_send_id.send_mail(response.id, force_send=True)
                send_count += 1

        if self.hr_emp and self.emp_survey_id and not self._existing_answer(self.emp_survey_id, self.emp_id):
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

        rec = self.env["hr.appraisal.stages"].search([("sequence", "=", 2)])
        self.with_context(appraisal_action=True).write({
            'state': rec.id,
            'check_sent': True,
            'check_draft': False,
            'check_initial': False,
        })

    def action_get_answers(self):
        res = super().action_get_answers()
        if res.get("domain", False):
            res["domain"] = [("appraisal_id", "=", self.ids[0])]
        return res

    def action_set_initial(self):
        res = super(HrAppraisal, self.with_context(appraisal_action=True)).action_set_initial()
        return res

    def action_done(self):
        res = super(HrAppraisal, self.with_context(appraisal_action=True)).action_done()
        return res

    def action_set_draft(self):
        res = super(HrAppraisal, self.with_context(appraisal_action=True)).action_set_draft()
        return res

    def action_cancel(self):
        res = super(HrAppraisal, self.with_context(appraisal_action=True)).action_cancel()
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

    def write(self, vals):
        # restrict change state - only allow through action buttons
        if 'state' in vals and not self.env.context.get('appraisal_action', False):
            raise ValidationError(_(
                "You cannot change the state of the appraisal directly."
                " Please use the available action buttons to change the state."))
        return super().write(vals)
