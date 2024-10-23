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

    @api.model
    def get_days_type(self):
        """
        This function returns a dict with items:
        key: number of days before notify
        value: id list of leave types
        format result: {2: [11], 5: [9, 7]}
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
            dict_result.update({days_notify: lt_days_ids.ids})

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

    def get_msg_absences_end_in_days(self, days_to_end):
        absence_ids = self.get_absences_end_in_days(days_to_end)


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
        total_no_notify = 0
        dict_days_type = self.get_days_type()
        # {2: [11], 5: [9, 7]}
        str_msg = ""
        for item in dict_days_type.items():
            days_to_end = item[0]
            list_ids_lt = item[1]
            str_date = (datetime.datetime.today().date() + datetime.timedelta(days=days_to_end)).strftime("%d/%m/%Y")
            str_msg += '\n' if str_msg else ''
            str_msg += f'Absències que finalitzen en {days_to_end} dies [{str_date}]:'
            for id_lt in list_ids_lt:
                lt_id = self.browse(id_lt)
                absence_ids = lt_id.get_absences_end_in_days(days_to_end)
                str_msg += f'\n\n\t{lt_id.name} [{len(absence_ids)}]\n\t'
                if len(absence_ids) == 0:
                    continue
                total_no_notify += len(absence_ids)
                str_msg += ('\n\t'.join([absence_id[0].name_get()[0][1] for absence_id in absence_ids]))
        return total_no_notify, str_msg
