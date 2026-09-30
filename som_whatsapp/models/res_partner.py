from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.phone_validation.tools import phone_validation


class ResPartner(models.Model):
    _inherit = "res.partner"

    whatsapp_channel_count = fields.Integer(
        compute="_compute_whatsapp_channel_count",
        compute_sudo=True,
        string="WhatsApp conversations",
    )

    def _compute_whatsapp_channel_count(self):
        Channel = self.env["mail.channel"].sudo()
        for partner in self:
            partner.whatsapp_channel_count = Channel.search_count(
                [
                    ("whatsapp_partner_id", "=", partner.id),
                    ("channel_type", "=", "gateway"),
                    ("gateway_id.gateway_type", "=", "whatsapp"),
                ]
            )

    def _som_whatsapp_get_token(self, field_name):
        self.ensure_one()
        phone = self[field_name]
        sanitized = phone_validation.phone_sanitize_numbers_w_record([phone], self)[
            phone
        ].get("sanitized")
        if not sanitized:
            raise UserError(_("Phone cannot be sanitized"))
        return sanitized[1:]

    def _som_whatsapp_get_or_create_channel(self, gateway, token, inbound=False):
        self.ensure_one()
        Mapping = self.env["res.partner.gateway.channel"]
        mapping = Mapping.search(
            [("partner_id", "=", self.id), ("gateway_id", "=", gateway.id)],
            limit=1,
        )
        if mapping:
            if mapping.gateway_token != token:
                mapping.gateway_token = token
        else:
            mapping = Mapping.create(
                {
                    "name": gateway.name,
                    "partner_id": self.id,
                    "gateway_id": gateway.id,
                    "gateway_token": token,
                }
            )

        Channel = self.env["mail.channel"]
        channel = Channel.search(
            [
                ("whatsapp_partner_id", "=", self.id),
                ("gateway_id", "=", gateway.id),
            ],
            limit=1,
        )
        if not channel:
            # Reuse a pre-existing OCA channel when it has the same remote number.
            channel = Channel.search(
                [
                    ("gateway_id", "=", gateway.id),
                    ("gateway_channel_token", "=", token),
                    ("channel_type", "=", "gateway"),
                    ("whatsapp_partner_id", "=", False),
                ],
                limit=1,
            )
            if channel:
                channel.write({"whatsapp_partner_id": self.id})
            else:
                channel = Channel.create(
                    {
                        "name": self.display_name,
                        "channel_type": "gateway",
                        "gateway_id": gateway.id,
                        "gateway_channel_token": token,
                        "company_id": gateway.company_id.id,
                        "whatsapp_partner_id": self.id,
                    }
                )
        elif channel.gateway_channel_token != token:
            channel.write({"gateway_channel_token": token})

        if inbound:
            channel.channel_member_ids.filtered(
                lambda member: member.partner_id == self.env.user.partner_id
            ).unlink()
        return channel

    def _whatsapp_get_channel(self, field_name, gateway):
        self.ensure_one()
        return self._som_whatsapp_get_or_create_channel(
            gateway, self._som_whatsapp_get_token(field_name)
        )

    def action_open_whatsapp_channel(self):
        self.ensure_one()
        channels = self.env["mail.channel"].sudo().search(
            [
                ("whatsapp_partner_id", "=", self.id),
                ("channel_type", "=", "gateway"),
                ("gateway_id.gateway_type", "=", "whatsapp"),
            ]
        )
        channels = channels.filtered(
            lambda channel: self.env.user in channel.gateway_id.member_ids
        )
        if not channels:
            raise AccessError(_("You are not allowed to open this WhatsApp conversation."))
        channels.with_user(self.env.user)._som_whatsapp_join_current_user()
        if len(channels) == 1:
            return {
                "type": "ir.actions.client",
                "tag": "mail.action_discuss",
                "params": {"default_active_id": "mail.channel_%s" % channels.id},
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("WhatsApp conversations"),
            "res_model": "mail.channel",
            "view_mode": "tree,form",
            "domain": [("id", "in", channels.ids)],
        }
