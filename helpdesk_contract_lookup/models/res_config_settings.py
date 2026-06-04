from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    helpdesk_contract_lookup_search_limit = fields.Integer(
        string="Default Search Limit",
        config_parameter="helpdesk_contract_lookup.search_limit",
        default=20,
    )

    helpdesk_contract_lookup_erp_partner_url_template = fields.Char(
        string="ERP Partner URL Template",
        config_parameter="helpdesk_contract_lookup.erp_partner_url_template",
    )
