from odoo import models


class MailGatewayWhatsappService(models.AbstractModel):
    _inherit = "mail.gateway.whatsapp"

    def _get_channel_vals(self, gateway, token, update):
        values = super()._get_channel_vals(gateway, token, update)
        # Gateway users are operators, not automatic subscribers to every chat.
        values["channel_member_ids"] = []
        return values

    def _get_channel(self, gateway, token, update, force_create=False):
        author = self._get_author(gateway, update)
        if author and author._name == "res.partner":
            return author._som_whatsapp_get_or_create_channel(
                gateway, str(token), inbound=True
            )
        channel = super()._get_channel(
            gateway, token, update, force_create=force_create
        )
        if channel:
            channel.channel_member_ids.filtered(
                lambda member: member.partner_id == self.env.user.partner_id
            ).unlink()
        return channel
