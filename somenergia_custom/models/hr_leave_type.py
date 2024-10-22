# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HRLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    som_eoa_notification_mail = fields.Boolean(
        string="End of absence notifications mail",
    )

    som_eoa_notification_days = fields.Integer(
        string="Days notification before",
        default=1,
    )
