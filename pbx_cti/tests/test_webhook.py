from unittest.mock import patch

import pytz

from odoo.tests.common import HttpCase, new_test_user, tagged

from odoo.addons.pbx_cti.controllers.webhook import _clean_phone


@tagged("post_install", "-at_install")
class TestPbxWebhook(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = new_test_user(
            cls.env, login="pbx_test_agent", groups="base.group_user",
            pbx_extension="test-pbx-901", tz="Europe/Madrid",
        )

    def test_phone_normalization(self):
        for raw, expected in (
            (None, ""), ("", ""), ("invalid", ""), ("+34 900-123-456", "900123456"),
            ("0034 900 123 456", "900123456"), ("900123456", "900123456"),
            ("341234567", "341234567"), ("+44 123456789", "44123456789"),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(_clean_phone(raw), expected)

    def test_missing_parameters_create_no_call(self):
        calls = self.env["crm.phonecall"]
        before = calls.search_count([])
        for params in ({"phone": "900000000"}, {"extension": self.agent.pbx_extension},
                       {"phone": "invalid", "extension": self.agent.pbx_extension}):
            with self.subTest(params=params):
                response = self.url_open("/api/info/ringring", data=params)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], "missing_params")
        self.assertEqual(calls.search_count([]), before)

    def test_unknown_extension_creates_no_call_or_notification(self):
        before = self.env["crm.phonecall"].search_count([])
        with patch.object(type(self.env["bus.bus"]), "_sendone") as notify:
            response = self.url_open("/api/info/ringring", data={
                "phone": "900000000", "extension": "test-pbx-missing",
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"result": "no_user", "extension": "test-pbx-missing"})
            notify.assert_not_called()
        self.assertEqual(self.env["crm.phonecall"].search_count([]), before)

    def test_incoming_call_creates_record_and_notifies_only_agent(self):
        for extension_key in ("extension", "ext"):
            with self.subTest(extension_key=extension_key), patch.object(
                type(self.env["bus.bus"]), "_sendone",
            ) as notify:
                callid = "test-pbx-call-" + extension_key
                response = self.url_open("/api/info/ringring", data={
                    "phone": "+34 900 123 456", extension_key: self.agent.pbx_extension, "callid": callid,
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"result": "ok", "phone": "900123456"})
                calls = self.env["crm.phonecall"].search([("som_pbx_call_id", "=", callid)])
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls.user_id, self.agent)
                self.assertEqual((calls.som_phone, calls.partner_phone), ("900123456", "900123456"))
                self.assertEqual((calls.direction, calls.state), ("in", "open"))
                self.assertEqual(calls.som_operator, self.agent.pbx_extension)
                notify.assert_called_once()
                channel, message_type, payload = notify.call_args.args
                self.assertEqual(channel, "pbx_cti_%s" % self.agent.id)
                self.assertEqual(message_type, "pbx_incoming_call")
                self.assertEqual(payload["phonecall_id"], calls.id)
                self.assertEqual(payload["phone"], "900123456")
                self.assertEqual(payload["callid"], callid)
                expected_time = pytz.utc.localize(calls.create_date).astimezone(
                    pytz.timezone(self.agent.tz),
                ).strftime("%H:%M:%S")
                self.assertEqual(payload["created_at"], expected_time)
