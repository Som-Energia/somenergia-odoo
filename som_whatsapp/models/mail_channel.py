from odoo import _, fields, models
from odoo.exceptions import AccessError


class MailChannel(models.Model):
    _inherit = "mail.channel"

    whatsapp_partner_id = fields.Many2one(
        "res.partner",
        string="WhatsApp partner",
        index=True,
        copy=False,
        ondelete="set null",
    )

    _sql_constraints = [
        (
            "unique_whatsapp_partner_gateway",
            "UNIQUE(whatsapp_partner_id, gateway_id)",
            "A partner can only have one WhatsApp conversation per gateway.",
        ),
    ]

    def _som_whatsapp_is_authorized_operator(self, user):
        self.ensure_one()
        gateway = self.sudo().gateway_id
        return user.has_group("mail_gateway.gateway_user") and user in gateway.member_ids

    def _som_whatsapp_join_current_user(self):
        for channel in self:
            user = self.env.user
            if not channel._som_whatsapp_is_authorized_operator(user):
                raise AccessError(_("You are not allowed to join this WhatsApp conversation."))
            if not channel.sudo().channel_member_ids.filtered(
                lambda member: member.partner_id == user.partner_id
            ):
                # The user is authorized by the gateway, but is not a channel
                # member yet, so the regular channel access check cannot apply.
                channel.sudo().add_members(
                    partner_ids=[user.partner_id.id], post_joined_message=False
                )

    def execute_command_leave(self, **kwargs):
        for channel in self:
            if (
                channel.channel_type == "gateway"
                and channel.gateway_id.gateway_type == "whatsapp"
            ):
                channel.action_unfollow()
            else:
                super(MailChannel, channel).execute_command_leave(**kwargs)
