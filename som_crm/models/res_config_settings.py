# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    som_crm_call_category_id = fields.Many2one(
        related='company_id.som_crm_call_category_id',
        readonly=False,
    )
