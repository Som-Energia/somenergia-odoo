from odoo import _, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    whatsapp_channel_count = fields.Integer(
        related="partner_id.whatsapp_channel_count",
        string="WhatsApp conversations",
    )

    def _whatsapp_get_channel(self, field_name, gateway):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Link a contact before starting a WhatsApp conversation."))
        return self.partner_id._whatsapp_get_channel(field_name, gateway)

    def action_open_whatsapp_channel(self):
        self.ensure_one()
        if not self.partner_id:
            return False
        return self.partner_id.action_open_whatsapp_channel()
