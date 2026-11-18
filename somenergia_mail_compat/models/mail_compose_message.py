from odoo import fields, models
from odoo.addons.mail.wizard.mail_compose_message import MailComposer


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    if "auto_comment" not in dict(MailComposer.message_type.selection):
        message_type = fields.Selection(
            selection_add=[("auto_comment", "Automated Targeted Notification")],
            ondelete={"auto_comment": "set notification"},
        )
