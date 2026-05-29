from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_open_contract_lookup(self):
        self.ensure_one()
        vat_value = (self.vat or "").strip()
        if vat_value.upper().startswith("ES"):
            vat_value = vat_value[2:]
        vat_value = vat_value.strip()

        return {
            "type": "ir.actions.client",
            "tag": "helpdesk_contract_lookup.main",
            "params": {
                "field": "nif",
                "value": vat_value,
                "auto_search": bool(vat_value),
            },
        }
