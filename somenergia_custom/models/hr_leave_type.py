# -*- coding: utf-8 -*-
import logging
import datetime
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class HRLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    som_eoa_notification_mail = fields.Boolean(
        string="End of absence notifications mail",
    )

    som_eoa_notification_days = fields.Integer(
        string="Days notification before",
        default=1,
    )

    som_mandatory_description = fields.Boolean(
        string="Mandatory description",
        default=False,
    )

    @api.model
    def get_days_notify_types(self):
        """
        This function returns a dict with items:
        key: number of days before notify
        value: id list of leave types
        format result: {2: [11], 5: [7, 9]}
        """
        lt_ids = self.env['hr.leave.type'].search([
            ('som_eoa_notification_mail', '=', True),
        ])

        list_days_notify = set(list(lt_ids.mapped('som_eoa_notification_days')))
        dict_result = {}
        for days_notify in list_days_notify:
            lt_days_ids = lt_ids.filtered(
                lambda x: x.som_eoa_notification_days == days_notify
            )
            dict_result.update({days_notify: sorted(lt_days_ids.ids)})

        return dict_result

    def get_absences_end_in_days(self, days_to_end):
        self.ensure_one()
        date_to = datetime.datetime.today().date() + datetime.timedelta(days=days_to_end)
        domain = [
            ('holiday_status_id', '=', self.id),
            ('request_date_to', '=', fields.Date.to_string(date_to)),
            ('state', 'in', ['validate', 'confirm']),
        ]
        return self.env['hr.leave'].search(domain)

    @api.model
    def get_end_of_absences_mail_text(self):
        """
        We could get a message like this:
        Absències que finalitzen en 10 dies [02/11/2024]:

            Maternitat/Paternitat legal [0]

        Absències que finalitzen en 7 dies [30/10/2024]:

            Visita mèdica [1]
            NOM 1 a Visita mèdica: 63.00 hores 18/10/2024

            Baixa Mèdica [2]
            NOM 2 en Baixa Mèdica: 20.00 dies (03/10/2024 / 30/10/2024)
            NOM 3 en Baixa Mèdica: 42.00 dies (02/09/2024 / 30/10/2024)
        """
        total_to_notify = 0
        dict_days_type = self.get_days_notify_types()
        # {2: [11], 5: [7, 9]}
        str_msg = ""
        for item in dict_days_type.items():
            days_to_end = item[0]
            list_ids_lt = item[1]
            str_date = (datetime.datetime.today().date() + datetime.timedelta(days=days_to_end)).strftime("%d/%m/%Y")
            str_msg += '<br/>' if str_msg else ''
            str_msg += f'<strong>Absències que finalitzen en {days_to_end} dies [{str_date}]:</strong>'
            for id_lt in list_ids_lt:
                lt_id = self.browse(id_lt)
                absence_ids = lt_id.get_absences_end_in_days(days_to_end)
                str_msg += f'<br/><br/>{lt_id.name} [{len(absence_ids)}]<br/>'
                if len(absence_ids) == 0:
                    continue
                total_to_notify += len(absence_ids)
                str_msg += ('<br/>'.join([absence_id[0].name_get()[0][1] for absence_id in absence_ids]))
        return total_to_notify, str_msg

    @api.model
    def send_mail_end_of_absences_reminder(self):
        total_no_notify, str_mail_body = self.get_end_of_absences_mail_text()
        if total_no_notify == 0:
            return
        somadmin_user_id = self.env.ref('base.somadmin')
        try:
            mail_html = _("""
                            <div style="margin: 0px; padding: 0px;">
                                <p style="margin: 0px; padding: 0px; font-size: 13px;">
                                    Hola,
                                    <br/><br/>
                                    Aquest és el llistat d'absències que finalitzen aviat:
                                    <br/><br/>
                                    %s
                                    <br/><br/>
                                    <a t-att-href="object.signup_url" style="background-color:#875A7B; padding:8px 16px 8px 16px; text-decoration:none; color:#fff; border-radius:5px" href="https://odoo.somenergia.coop/web#action=321&model=hr.leave&view_type=list&cids=1&menu_id=214" target="_blank" class="btn btn-primary">Veure Absències</a>
                                    <br/><br/>
                                    Salut!
                                </p>
                            </div>
                        """) % (
                    str_mail_body,
            )

            mail_values = {
                'author_id': somadmin_user_id.partner_id.id,
                'body_html': mail_html,
                'subject': _('Odoo Som - Absències que finalitzen aviat'),
                'email_from':
                    somadmin_user_id.email_formatted or somadmin_user_id.company_id.catchall or
                    somadmin_user_id.company_id.email,
                'email_to': self.env["ir.config_parameter"].sudo().get_param("som_mail_entorn_laboral"),
                'auto_delete': False,
            }

            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()

        except Exception as e:
            _logger.exception("End of absences reminder - Unable to send email.")
