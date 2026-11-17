import json
from unittest.mock import MagicMock, patch

from odoo.exceptions import ValidationError
from odoo.tests.common import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestLookupHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = new_test_user(
            cls.env, login="lookup_test_agent", password="lookup_test_agent",
            groups="base.group_user,helpdesk_mgmt.group_helpdesk_user", tz="UTC",
        )
        cls.other = new_test_user(
            cls.env, login="lookup_test_other", password="lookup_test_other", groups="base.group_user",
        )
        cls.partner = cls.env["res.partner"].create({"name": "Lookup partner", "som_erp_id": 987654321})
        cls.call = cls.env["crm.phonecall"].create({"name": "Lookup call", "user_id": cls.agent.id})

    def _json_rpc(self, path, params):
        response = self.url_open(
            path,
            data=json.dumps({"jsonrpc": "2.0", "method": "call", "params": params, "id": 1}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def rpc(self, endpoint, **params):
        return self._json_rpc("/helpdesk_contract_lookup/" + endpoint, params)

    def model_rpc(self, method, **kwargs):
        model = "helpdesk.contract.lookup.service"
        api = getattr(getattr(type(self.env[model]), method), "_api", None)
        return self._json_rpc("/web/dataset/call_kw", {
            "model": model,
            "method": method,
            "args": [] if api == "model" else [[]],
            "kwargs": kwargs,
        })

    def login_agent(self):
        self.authenticate(self.agent.login, self.agent.login)

    def test_model_rpc_rejects_non_helpdesk_user(self):
        self.authenticate(self.other.login, self.other.login)
        self.assertFalse(self.other.has_group("helpdesk_mgmt.group_helpdesk_user"))
        service = type(self.env["helpdesk.contract.lookup.service"])
        client = MagicMock()
        client.model.return_value.search.return_value = []
        with patch.object(service, "_get_erp_client", return_value=client) as connect:
            for method, params in (
                ("search", {"field": "name", "value": "Example"}),
                ("contract_details", {"contract_numbers": ["C005"]}),
                ("contract_details", {"contract_numbers": []}),
            ):
                with self.subTest(method=method, params=params):
                    result = self.model_rpc(method, **params)
                    self.assertIn("error", result)
                    self.assertEqual(result["error"]["data"]["name"], "odoo.exceptions.AccessError")
            connect.assert_not_called()

    def test_model_rpc_allows_helpdesk_user(self):
        self.login_agent()
        service = type(self.env["helpdesk.contract.lookup.service"])
        client = MagicMock()
        client.model.return_value.search.return_value = []
        with patch.object(service, "_get_erp_client", return_value=client) as connect:
            empty = self.model_rpc("contract_details", contract_numbers=[])
            self.assertEqual(empty["result"], {"status": "ok", "contracts": {}})
            connect.assert_not_called()
            details = self.model_rpc("contract_details", contract_numbers=["C005"])
            self.assertEqual(details["result"], {"status": "no_info", "contracts": {}})
            connect.assert_called_once_with()

    def test_all_routes_reject_non_helpdesk_user(self):
        self.authenticate(self.other.login, self.other.login)
        for endpoint in (
            "search", "contract_details", "phonecall_form_view_id", "link_partner_to_call",
            "open_partner_in_odoo", "register_incoming_call", "partner_phonecalls",
        ):
            with self.subTest(endpoint=endpoint):
                result = self.rpc(endpoint)
                self.assertEqual(result["error"]["data"]["name"], "odoo.exceptions.AccessError")

    def test_search_requires_authentication(self):
        result = self.rpc("search", field="name", value="Example")
        self.assertIn("error", result)
        self.assertNotIn("result", result)

    def test_search_and_contract_details_delegate_to_service(self):
        self.login_agent()
        service = type(self.env["helpdesk.contract.lookup.service"])
        for endpoint, params, expected in (
            ("search", {"field": "name", "value": "Example", "limit": 5}, {"status": "no_info", "partners": []}),
            ("contract_details", {"contract_numbers": ["C005"]}, {"status": "ok", "contracts": {}}),
        ):
            with self.subTest(endpoint=endpoint), patch.object(service, endpoint, return_value=expected) as method:
                self.assertEqual(self.rpc(endpoint, **params)["result"], expected)
                method.assert_called_once_with(**params)
        with patch.object(service, "search", side_effect=ValidationError("Invalid field")):
            result = self.rpc("search", field="unknown", value="x")
            self.assertEqual(result["error"]["data"]["name"], "odoo.exceptions.ValidationError")

    def test_link_call_reuses_partner_and_updates_contract(self):
        self.login_agent()
        result = self.rpc(
            "link_partner_to_call", phonecall_id=self.call.id, partner_id=self.partner.som_erp_id,
            partner_name=self.partner.name, partner_vat=False, contract_name="C005",
        )
        self.assertEqual(result["result"], {"status": "ok"})
        self.call.invalidate_recordset()
        self.assertEqual(self.call.partner_id, self.partner)
        self.assertEqual(self.call.som_caller_erp_id, self.partner.som_erp_id)
        self.assertEqual(self.call.som_contract_name, "C005")
        self.assertEqual(self.call.som_caller_name, self.partner.name)

    def test_open_partner_creates_once_and_registers_incoming_call(self):
        self.login_agent()
        params = {"partner_id": 987654322, "partner_name": "New lookup partner", "partner_vat": False}
        first = self.rpc("open_partner_in_odoo", **params)["result"]["odoo_partner_id"]
        second = self.rpc("open_partner_in_odoo", **params)["result"]["odoo_partner_id"]
        self.assertEqual(first, second)
        result = self.rpc("register_incoming_call", partner_phone="900000000", **params)
        call = self.env["crm.phonecall"].browse(result["result"]["phonecall_id"])
        self.assertEqual(call.partner_id.id, first)
        self.assertEqual(call.user_id, self.agent)
        self.assertEqual((call.state, call.direction, call.som_phone), ("open", "in", "900000000"))

    def test_required_parameters_and_missing_call(self):
        self.login_agent()
        for endpoint, params in (
            ("link_partner_to_call", {}), ("open_partner_in_odoo", {}),
            ("register_incoming_call", {}), ("partner_phonecalls", {}),
            ("link_partner_to_call", {"phonecall_id": 2147483647, "partner_id": self.partner.som_erp_id}),
        ):
            with self.subTest(endpoint=endpoint, params=params):
                result = self.rpc(endpoint, **params)
                self.assertEqual(result["error"]["data"]["name"], "odoo.exceptions.ValidationError")

    def test_phonecalls_are_filtered_formatted_and_use_lookup_view(self):
        category = self.env["product.category"].create({"name": "Lookup category", "som_color": 2})
        self.call.write({
            "partner_id": self.partner.id, "duration": 1.5,
            "date": "2026-01-01 12:00:00", "som_contract_name": "C005",
            "som_category_ids": [(6, 0, category.ids)],
        })
        self.login_agent()
        result = self.rpc("partner_phonecalls", partner_id=self.partner.som_erp_id)["result"]
        self.assertTrue(result["odoo_partner_found"])
        self.assertEqual([call["id"] for call in result["phonecalls"]], [self.call.id])
        self.assertEqual(result["phonecalls"][0]["duration"], "1:30")
        self.assertEqual(result["phonecalls"][0]["date"], "2026-01-01 12:00")
        self.assertEqual(result["phonecalls"][0]["contract_name"], "C005")
        self.assertEqual(result["phonecalls"][0]["categories"], [{"name": "Lookup category", "color": "#F4A460"}])
        missing = self.rpc("partner_phonecalls", partner_id=987654323)["result"]
        self.assertEqual(missing, {"phonecalls": [], "odoo_partner_found": False})
        view = self.rpc("phonecall_form_view_id")["result"]["view_id"]
        self.assertEqual(view, self.env.ref("helpdesk_contract_lookup.view_crm_phonecall_form_lookup").id)
