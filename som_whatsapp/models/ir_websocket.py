from odoo import models


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _build_bus_channel_list(self, channels):
        channels = super()._build_bus_channel_list(channels)
        if not self.env.user or self.env.user._is_public():
            return channels
        member_channel_ids = set(self.env.user.partner_id.channel_ids.ids)
        return [
            channel
            for channel in channels
            if getattr(channel, "_name", None) != "mail.channel"
            or channel.channel_type != "gateway"
            or channel.id in member_channel_ids
        ]
