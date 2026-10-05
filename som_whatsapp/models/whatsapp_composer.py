from odoo import models


class WhatsappComposer(models.TransientModel):
    _inherit = "whatsapp.composer"

    def _action_send_whatsapp(self):
        record = self.env[self.res_model].browse(self.res_id)
        if not record:
            return
        channel = record._whatsapp_get_channel(self.number_field_name, self.gateway_id)
        channel._som_whatsapp_join_current_user()
        channel.with_context(whatsapp_template_id=self.template_id.id).message_post(
            body=self.body, subtype_xmlid="mail.mt_comment", message_type="comment"
        )

    def action_view_whatsapp(self):
        self.ensure_one()
        record = self.env[self.res_model].browse(self.res_id)
        if not record:
            return False
        channel = record._whatsapp_get_channel(self.number_field_name, self.gateway_id)
        channel._som_whatsapp_join_current_user()
        return {
            "type": "ir.actions.client",
            "tag": "som_whatsapp.action_discuss",
            "context": {"active_id": "mail.channel_%s" % channel.id},
        }
