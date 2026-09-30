from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestPartnerWhatsapp(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        internal_user_group = cls.env.ref("base.group_user")
        gateway_group = cls.env.ref("mail_gateway.gateway_user")
        cls.other_operator = cls.env["res.users"].create(
            {
                "name": "WhatsApp operator",
                "login": "whatsapp.operator@example.com",
                "email": "whatsapp.operator@example.com",
                "groups_id": [
                    (4, internal_user_group.id),
                    (4, gateway_group.id),
                ],
            }
        )
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "WhatsApp",
                "gateway_type": "whatsapp",
                "token": "test-token",
                "member_ids": [(4, cls.env.user.id), (4, cls.other_operator.id)],
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "WhatsApp partner", "mobile": "+34600000000"}
        )

    def test_partner_channel_does_not_add_gateway_members(self):
        channel = self.partner._whatsapp_get_channel("mobile", self.gateway)

        self.assertEqual(channel.whatsapp_partner_id, self.partner)
        self.assertEqual(channel.gateway_id, self.gateway)
        self.assertIn(self.env.user.partner_id, channel.channel_member_ids.partner_id)
        self.assertNotIn(self.other_operator.partner_id, channel.channel_member_ids.partner_id)

    def test_partner_action_joins_operator(self):
        channel = self.partner._whatsapp_get_channel("mobile", self.gateway)

        action = self.partner.with_user(self.other_operator).action_open_whatsapp_channel()

        self.assertEqual(action["tag"], "mail.action_discuss")
        self.assertIn(self.other_operator.partner_id, channel.channel_member_ids.partner_id)

    def test_removed_gateway_operator_no_longer_receives_updates(self):
        channel = self.partner._whatsapp_get_channel("mobile", self.gateway)
        self.partner.with_user(self.other_operator).action_open_whatsapp_channel()
        self.gateway.member_ids -= self.other_operator

        self.assertIn(self.other_operator.partner_id, channel.channel_member_ids.partner_id)
        self.assertFalse(channel._som_whatsapp_is_authorized_operator(self.other_operator))

    def test_partner_action_joins_operator_on_all_gateway_channels(self):
        first_channel = self.partner._whatsapp_get_channel("mobile", self.gateway)
        second_gateway = self.env["mail.gateway"].create(
            {
                "name": "Second WhatsApp",
                "gateway_type": "whatsapp",
                "token": "second-test-token",
                "member_ids": [(4, self.other_operator.id)],
            }
        )
        second_channel = self.partner._whatsapp_get_channel(
            "mobile", second_gateway
        )

        action = self.partner.with_user(self.other_operator).action_open_whatsapp_channel()

        self.assertEqual(action["res_model"], "mail.channel")
        self.assertIn(self.other_operator.partner_id, first_channel.channel_member_ids.partner_id)
        self.assertIn(self.other_operator.partner_id, second_channel.channel_member_ids.partner_id)

    def test_phone_change_updates_channel_destination(self):
        channel = self.partner._whatsapp_get_channel("mobile", self.gateway)
        self.partner.mobile = "+34600000001"

        self.partner._whatsapp_get_channel("mobile", self.gateway)

        mapping = self.env["res.partner.gateway.channel"].search(
            [
                ("partner_id", "=", self.partner.id),
                ("gateway_id", "=", self.gateway.id),
            ]
        )
        self.assertEqual(mapping.gateway_token, "34600000001")
        self.assertEqual(channel.gateway_channel_token, "34600000001")

    def test_non_operator_cannot_join_partner_channel(self):
        self.partner._whatsapp_get_channel("mobile", self.gateway)
        user = self.env["res.users"].create(
            {
                "name": "Unauthorized operator",
                "login": "unauthorized.operator@example.com",
                "groups_id": [(4, self.env.ref("base.group_user").id)],
            }
        )

        with self.assertRaises(AccessError):
            self.partner.with_user(user).action_open_whatsapp_channel()

    def test_lead_action_opens_partner_channel(self):
        channel = self.partner._whatsapp_get_channel("mobile", self.gateway)
        lead = self.env["crm.lead"].create(
            {"name": "WhatsApp lead", "partner_id": self.partner.id}
        )

        action = lead.with_user(self.other_operator).action_open_whatsapp_channel()

        self.assertEqual(
            action["params"]["active_id"], "mail.channel_%s" % channel.id
        )
        self.assertIn(self.other_operator.partner_id, channel.channel_member_ids.partner_id)

    def test_inbound_channel_removes_webhook_user(self):
        channel = self.partner._som_whatsapp_get_or_create_channel(
            self.gateway, "34600000000", inbound=True
        )

        self.assertNotIn(self.env.user.partner_id, channel.channel_member_ids.partner_id)
