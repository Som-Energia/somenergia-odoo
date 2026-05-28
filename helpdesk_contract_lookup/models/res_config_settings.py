from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    helpdesk_contract_lookup_search_limit = fields.Integer(
        string="Default Search Limit",
        config_parameter="helpdesk_contract_lookup.search_limit",
        default=20,
    )
