# -*- coding: utf-8 -*-
from odoo import models, fields

class CrmStage(models.Model):
    _inherit = 'crm.stage'

    som_upcoming_activity_days = fields.Integer(
        string='Days next activity',
        required=False,
        help="Number of days until the next upcoming activity",
    )
