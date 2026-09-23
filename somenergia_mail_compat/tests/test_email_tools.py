from odoo import tools
from odoo.tests.common import TransactionCase


class TestEmailSplitAndFormatNormalize(TransactionCase):
    def test_normalizes_and_preserves_display_name(self):
        recipients = 'Maria Example <MARIA.EXAMPLE@EXAMPLE.COM>, SECOND@EXAMPLE.COM'

        self.assertEqual(
            tools.email_split_and_format_normalize(recipients),
            ['"Maria Example" <maria.example@example.com>', 'second@example.com'],
        )

    def test_anonymizes_email_for_mail_logs(self):
        self.assertEqual(
            tools.mail.email_anonymize("admin@example.com"),
            "a****@example.com",
        )
        self.assertEqual(
            tools.mail.email_anonymize("portal@example.com"),
            "p***al@example.com",
        )
        self.assertEqual(
            tools.mail.email_anonymize("portal@example.com", redact_domain=True),
            "p***al@e******.com",
        )
        self.assertFalse(tools.mail.email_anonymize(False))
