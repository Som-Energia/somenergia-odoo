# -*- coding: utf-8 -*-
import logging
import datetime

from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
from datetime import datetime
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

    def get_absences_end_days_to(self, days_to):
        self.ensure_one()
        date_to = datetime.today().date() + datetime.timedelta(days=days_to)
        domain = [
            ('holiday_status_id', '=', self.id),
            ('request_date_to', '=', fields.Date.to_string(date_to)),
            ('state', 'in', ['validate', 'confirm']),
        ]
        return self.search(domain)

    @api.model
    def send_mail_end_of_absences_reminder(self):
        dict_days_type = self.get_days_type()
        # {2: [11], 5: [9, 7]}
        str_msg = ""
        for key in dict_days_type.keys():
            str_msg = f'Absències que finalitzen en {key} dies: \n'
        try:
            pass

        except Exception as e:
            pass
