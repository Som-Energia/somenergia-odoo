from odoo import fields, models


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

    def _som_whatsapp_join_current_user(self):
        for channel in self:
            partner = self.env.user.partner_id
            if not channel.channel_member_ids.filtered(
                lambda member: member.partner_id == partner
            ):
                channel.add_members(
                    partner_ids=[partner.id], post_joined_message=False
                )
