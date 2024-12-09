# -*- coding: utf-8 -*-
from odoo import fields, models, _


class StressDay(models.Model):
    _inherit = 'hr.leave.stress.day'

    som_type = fields.Selection(
        selection=[
            ("no_service", _("No service")),
            ("others", _("Others")),
        ],
        string="Type",
        required=False,
    )
