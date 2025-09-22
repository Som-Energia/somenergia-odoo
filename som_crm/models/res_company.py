# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    som_crm_call_category_id = fields.Many2one(
        string="CRM Category",
        comodel_name="product.category",
        domain="[('som_level', '=', 3)]",
    )

    som_ff_call_to_opportunity = fields.Boolean(
        string="Feature flag: Automatic Call to Opportunity conversion by Category",
    )
