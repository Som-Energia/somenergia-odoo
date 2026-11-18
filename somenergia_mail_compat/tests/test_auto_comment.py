from email.message import EmailMessage
from unittest.mock import patch

from odoo.addons.mail.models.mail_thread import MailThread
from odoo.addons.mail.tests.common import MailCase
from odoo.tests.common import TransactionCase


class TestAutoComment(MailCase, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].with_context(
            mail_create_nolog=True, mail_create_nosubscribe=True
        ).create({"name": "Compatibility record", "email": "record@example.com"})
        cls.template = cls.env["mail.template"].create({
            "name": "Compatibility acknowledgement",
            "model_id": cls.env.ref("base.model_res_partner").id,
            "subject": "Automatic acknowledgement",
            "body_html": "<p>We received your request.</p>",
        })

    def _parent(self, message_type, subtype="mail.mt_note"):
        return self.env["mail.message"].create({
            "model": "res.partner",
            "res_id": self.partner.id,
            "body": "Original message",
            "message_type": message_type,
            "subtype_id": self.env.ref(subtype).id,
        })

    def _reply(self, parent):
        message = EmailMessage()
        message["From"] = "Customer <customer@example.com>"
        message["To"] = "support@example.com"
        message["Subject"] = "Re: Automatic acknowledgement"
        message["Message-ID"] = "<compat-reply-%s@example.com>" % parent.id
        message["In-Reply-To"] = parent.message_id
        message["References"] = parent.message_id
        message.set_content("Here is some more information.")
        return message

    def _post_tracking_template(self, **kwargs):
        options = {"subtype_id": self.env.ref("mail.mt_note").id, **kwargs}
        self.patch(
            type(self.partner), "_track_template",
            lambda record, changes: {"name": (self.template, options)},
        )
        before = self.partner.message_ids
        with self.mock_mail_gateway():
            self.partner._message_track_post_template({"name"})
        return self.partner.message_ids - before

    def test_message_and_composer_accept_auto_comment(self):
        for model in ("mail.message", "mail.compose.message"):
            with self.subTest(model=model):
                field = self.env[model]._fields["message_type"]
                self.assertIn("auto_comment", field.get_values(self.env))

    def test_tracking_template_defaults_to_auto_comment(self):
        messages = self._post_tracking_template()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages.message_type, "auto_comment")

    def test_tracking_template_preserves_explicit_type(self):
        messages = self._post_tracking_template(message_type="notification")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages.message_type, "notification")

    def test_mass_mail_keeps_the_native_email_type(self):
        messages = self._post_tracking_template(composition_mode="mass_mail")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages.message_type, "email")

    def test_tracking_template_options_are_not_mutated(self):
        options = {"subtype_id": self.env.ref("mail.mt_note").id}
        self.patch(
            type(self.partner), "_track_template",
            lambda record, changes: {"name": (self.template, options)},
        )
        with self.mock_mail_gateway():
            self.partner._message_track_post_template({"name"})
        self.assertEqual(options, {"subtype_id": self.env.ref("mail.mt_note").id})

    def test_native_tracking_is_delegated_without_changes(self):
        from ..models import mail_thread

        changes = {"name"}
        with patch.object(mail_thread, "HAS_NATIVE_AUTO_COMMENT", True), patch.object(
            MailThread, "_message_track_post_template", return_value="native"
        ) as native:
            result = self.partner._message_track_post_template(changes)
        self.assertEqual(result, "native")
        native.assert_called_once_with(changes)

    def test_tracking_qweb_templates_receive_the_same_default(self):
        self.patch(
            type(self.partner), "_track_template",
            lambda record, changes: {"name": ("mail.some_view", {})},
        )
        with patch.object(type(self.partner), "message_post_with_view") as post:
            self.partner._message_track_post_template({"name"})
        post.assert_called_once_with("mail.some_view", message_type="auto_comment")

    def test_tracking_without_changes_does_not_post(self):
        with patch.object(type(self.partner), "_track_template") as templates:
            self.assertTrue(self.partner._message_track_post_template(set()))
        templates.assert_not_called()

    def test_uninstall_policy_preserves_messages(self):
        from ..models.mail_message import HAS_NATIVE_AUTO_COMMENT

        if HAS_NATIVE_AUTO_COMMENT:
            self.skipTest("The selection is owned by the native core")
        for model in ("mail.message", "mail.compose.message"):
            with self.subTest(model=model):
                self.assertEqual(
                    self.env[model]._fields["message_type"].ondelete["auto_comment"],
                    "set notification",
                )

    def test_reply_to_auto_comment_is_not_internal(self):
        parent = self._parent("auto_comment")
        parsed = self.env["mail.thread"].message_parse(self._reply(parent))
        self.assertEqual(parsed["parent_id"], parent.id)
        self.assertFalse(parsed["is_internal"])

    def test_native_parsing_is_not_overridden(self):
        from ..models import mail_thread

        parent = self._parent("auto_comment")
        values = {"parent_id": parent.id, "is_internal": True}
        reply = self._reply(parent)
        with patch.object(mail_thread, "HAS_NATIVE_AUTO_COMMENT", True), patch.object(
            MailThread, "message_parse", return_value=values
        ) as native:
            parsed = self.env["mail.thread"].message_parse(reply)
        self.assertIs(parsed, values)
        self.assertTrue(parsed["is_internal"])
        native.assert_called_once_with(reply, save_original=False)

    def test_reply_to_internal_note_stays_internal(self):
        for message_type in ("comment", "notification"):
            with self.subTest(message_type=message_type):
                parent = self._parent(message_type)
                parsed = self.env["mail.thread"].message_parse(self._reply(parent))
                self.assertEqual(parsed["parent_id"], parent.id)
                self.assertTrue(parsed["is_internal"])

    def test_gateway_reply_to_auto_comment_becomes_discussion(self):
        follower = self.env["res.partner"].create({
            "name": "External follower", "email": "follower@example.com",
        })
        self.partner.message_subscribe(partner_ids=follower.ids)
        parent = self._parent("auto_comment")
        reply = self._reply(parent)
        with self.mock_mail_gateway():
            self.env["mail.thread"].with_context(
                mail_notify_force_send=False
            ).message_process(
                "res.partner", reply.as_bytes(), thread_id=self.partner.id
            )
        message = self.env["mail.message"].search([
            ("message_id", "=", reply["Message-ID"]),
        ])
        self.assertEqual(len(message), 1)
        self.assertEqual(message.parent_id, parent)
        self.assertFalse(message.is_internal)
        self.assertEqual(message.subtype_id, self.env.ref("mail.mt_comment"))
        self.assertIn(follower, message.notified_partner_ids)

    def test_gateway_reply_to_internal_note_stays_private(self):
        follower = self.env["res.partner"].create({
            "name": "External follower", "email": "follower@example.com",
        })
        self.partner.message_subscribe(partner_ids=follower.ids)
        parent = self._parent("comment")
        reply = self._reply(parent)
        with self.mock_mail_gateway():
            self.env["mail.thread"].with_context(
                mail_notify_force_send=False
            ).message_process(
                "res.partner", reply.as_bytes(), thread_id=self.partner.id
            )
        message = self.env["mail.message"].search([
            ("message_id", "=", reply["Message-ID"]),
        ])
        self.assertEqual(len(message), 1)
        self.assertEqual(message.parent_id, parent)
        self.assertTrue(message.is_internal)
        self.assertEqual(message.subtype_id, self.env.ref("mail.mt_note"))
        self.assertNotIn(follower, message.notified_partner_ids)
