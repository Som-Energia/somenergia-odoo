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
        string="Automatic Call to Opportunity conversion by Category",
    )

    som_ff_send_lead_confirmation_email = fields.Boolean(
        string="Send confirmation email when a lead is created through API",
    )

    som_ff_send_lead_confirmation_email_from = fields.Char(
        string="Mail From for lead confirmation email",
    )

    som_ff_auto_upcomming_activity = fields.Boolean(
        string="Automatic Upcoming Activity creation on Lead creation",
    )

    som_crm_date_from_import_gsheets = fields.Date(
        string="Date from Google Sheets import",
        help="Date from which leads will be imported from Google Sheets. If empty, all leads will be imported.",
    )
