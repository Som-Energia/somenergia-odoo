# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    som_erp_id = fields.Integer(
        string="ERP Partner ID",
        help="Partner ID in the external ERP (OpenERP 5).",
    )
