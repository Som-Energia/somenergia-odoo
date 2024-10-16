# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    som_restrictive_stress_days = fields.Boolean(
        related='company_id.som_restrictive_stress_days',
        readonly=False,
    )
