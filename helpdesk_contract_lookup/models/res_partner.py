from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_open_contract_lookup(self):
        self.ensure_one()

        # Use ERP partner id if mapped, fallback to NIF
        erp_id = getattr(self, "som_erp_id", None)
        if erp_id:
            return {
                "type": "ir.actions.client",
                "tag": "helpdesk_contract_lookup.main",
                "params": {
                    "field": "partner_id",
                    "value": str(erp_id),
                    "auto_search": True,
                },
            }

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
