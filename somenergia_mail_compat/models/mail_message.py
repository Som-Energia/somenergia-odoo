from odoo import fields, models
from odoo.addons.mail.models.mail_message import Message


# Inspect the core definition, not a registry already extended by this addon.
HAS_NATIVE_AUTO_COMMENT = "auto_comment" in dict(Message.message_type.selection)


class MailMessage(models.Model):
    _inherit = "mail.message"

    if not HAS_NATIVE_AUTO_COMMENT:
        message_type = fields.Selection(
            selection_add=[("auto_comment", "Automated Targeted Notification")],
            ondelete={"auto_comment": "set notification"},
        )
