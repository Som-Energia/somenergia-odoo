# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    som_restrictive_stress_days = fields.Boolean(
        string="Restrictive stress days",
        default=True,
    )
