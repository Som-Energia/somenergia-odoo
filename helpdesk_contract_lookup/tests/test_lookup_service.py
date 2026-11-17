from unittest.mock import MagicMock, patch

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user


class TestLookupService(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = new_test_user(
            cls.env, login="lookup_service_agent",
            groups="base.group_user,helpdesk_mgmt.group_helpdesk_user",
        )
        cls.other = new_test_user(cls.env, login="lookup_service_other", groups="base.group_user")
        cls.portal = new_test_user(cls.env, login="lookup_service_portal", groups="base.group_portal")

    def setUp(self):
        super().setUp()
        self.service = self.env["helpdesk.contract.lookup.service"].with_user(self.agent)
        self.models = {}
        self.client = MagicMock()
        self.client.model.side_effect = self.models.__getitem__
        self.real_get_erp_client = self.service._get_erp_client
        self.patch(type(self.service), "_get_erp_client", lambda service: self.client)
        self.params = self.env["ir.config_parameter"].sudo()
        for kind in ("partner", "contract", "invoice"):
            self.params.set_param(
                "helpdesk_contract_lookup.erp_%s_url_template" % kind,
                "https://erp.example.test/%s/{res_id}" % kind,
            )

    def erp_model(self, name, ids=None, records=None):
        model = MagicMock()
        model.search.return_value = ids or []
        model.read.return_value = records or []
        self.models[name] = model
        return model

    def test_public_methods_reject_non_helpdesk_users(self):
        for model in ("res.partner", "giscedata.polissa"):
            self.erp_model(model)
        with patch.object(type(self.service), "_get_erp_client", return_value=self.client) as connect:
            for user in (self.other, self.portal):
                self.assertFalse(user.has_group("helpdesk_mgmt.group_helpdesk_user"))
                service = self.service.with_user(user)
                for method, params in (
                    ("search", {"field": "name", "value": "Example"}),
                    ("search", {"field": "unknown", "value": ""}),
                    ("contract_details", {"contract_numbers": ["C005"]}),
                    ("contract_details", {"contract_numbers": []}),
                    ("contract_details", {"contract_numbers": "invalid"}),
                ):
                    with self.subTest(user=user.login, method=method, params=params):
                        with self.assertRaises(AccessError):
                            getattr(service, method)(**params)
            connect.assert_not_called()

    def test_invalid_search_never_connects_to_erp(self):
        for field, value, limit in [("unknown", "x", 20), ("phone", "  ", 20), ("name", "x", "bad")]:
            with self.subTest(field=field, value=value, limit=limit):
                with self.assertRaises(ValidationError):
                    self.service.search(field, value, limit)
        self.client.model.assert_not_called()

    def test_search_limits_and_url_templates(self):
        self.params.set_param("helpdesk_contract_lookup.search_limit", "7")
        self.assertEqual(self.service._get_search_limit(None), 7)
        self.assertEqual(self.service._get_search_limit(-3), 1)
        self.params.set_param("helpdesk_contract_lookup.search_limit", "invalid")
        self.assertEqual(self.service._get_search_limit(None), 20)
        self.assertEqual(self.service._build_erp_invoice_url(12), "https://erp.example.test/invoice/12")
        self.params.set_param("helpdesk_contract_lookup.erp_invoice_url_template", "")
        self.assertEqual(self.service._build_erp_invoice_url(12), "")

    def test_search_uses_configured_limit_unless_explicitly_overridden(self):
        partner = self.erp_model("res.partner")
        for configured, params, expected in (
            ("7", {}, 7),
            ("7", {"limit": 3}, 3),
            ("invalid", {}, 20),
            (False, {}, 20),
        ):
            with self.subTest(configured=configured, params=params):
                self.params.set_param("helpdesk_contract_lookup.search_limit", configured)
                result = self.service.search("name", "Example", **params)
                self.assertEqual(result["limit"], expected)
                partner.search.assert_called_with([("name", "ilike", "Example")], limit=expected)

    def test_partner_search_domains(self):
        partner = self.erp_model("res.partner")
        for field, column in [("name", "name"), ("nif", "vat"), ("soci", "ref")]:
            with self.subTest(field=field):
                self.service._search_partner_ids(self.client, field, "Example", 5)
                partner.search.assert_called_with([(column, "ilike", "Example")], limit=5)
        self.service._search_partner_ids(self.client, "partner_id", "42", 5)
        partner.search.assert_called_with([("id", "=", 42)])
        with self.assertRaises(ValidationError):
            self.service._search_partner_ids(self.client, "partner_id", "invalid", 5)

    def test_phone_and_email_search_deduplicate_partners(self):
        address = self.erp_model("res.partner.address", [1, 2], [
            {"partner_id": [42, "Example"]}, {"partner_id": [42, "Example"]},
        ])
        self.erp_model("res.partner", records=[{"id": 42, "name": "Example"}])
        self.erp_model("giscedata.polissa")
        for field in ("phone", "email"):
            with self.subTest(field=field):
                result = self.service.search(field, "  example  ")
                self.assertEqual(result["count"], 1)
                self.assertEqual(result["value"], "example")
                self.assertEqual(result["partners"][0]["id"], 42)
                domain = (["|", ("phone", "like", "example"), ("mobile", "like", "example")]
                          if field == "phone" else [("email", "ilike", "example")])
                address.search.assert_called_with(domain)

    def test_empty_search_result(self):
        self.erp_model("res.partner.address")
        result = self.service.search("phone", "900000000")
        self.assertEqual(result["status"], "no_info")
        self.assertEqual(result["partners"], [])
        self.assertFalse(result["too_many"])

    def test_search_reports_truncation(self):
        self.erp_model("res.partner", [42, 43], [{"id": 42, "name": "Example"}])
        self.erp_model("giscedata.polissa")
        result = self.service.search("name", "Example", limit=1)
        self.assertTrue(result["too_many"])
        self.assertEqual(result["count"], 1)
        self.models["res.partner"].read.assert_called_once()
        self.assertEqual(len(self.models["res.partner"].read.call_args.args[0]), 1)

    def test_contract_search_collects_all_roles_and_truncates_cups(self):
        contracts = self.erp_model("giscedata.polissa", [5], [{
            "titular": [42, "Holder"], "pagador": [43, "Payer"], "soci": [42, "Holder"],
        }])
        ids = self.service._search_contract_partner_ids(self.client, "cups", "ES" + "1" * 22, 10)
        self.assertEqual(set(ids), {42, 43})
        contracts.search.assert_called_once_with(
            [("cups.name", "ilike", "ES" + "1" * 18)], limit=10, context={"active_test": False},
        )

    def test_partner_summary_groups_contracts_and_deduplicates_phones(self):
        self.erp_model("res.partner", records=[{
            "id": 42, "name": "Example", "www_phone": "900000000", "www_mobile": "900000000",
            "www_municipi": [1, {"name": "Girona"}], "empowering_token": "test-token",
        }])
        self.erp_model("giscedata.polissa", [5], [{
            "id": 5, "name": "C005", "titular": [42, "Example"], "pagador": [42, "Example"],
            "cups": [8, "ES123"], "active": False,
        }])
        self.erp_model("giscedata.cups.ps", records=[{
            "id": 8, "direccio": "Example Street", "id_municipi": [1, "Girona"],
        }])
        partner = self.service._build_partner_summary(self.client, [42], 20)[0]
        self.assertEqual(partner["phones"], ["900000000"])
        self.assertEqual(partner["city"], "Girona")
        self.assertTrue(partner["ov"])
        self.assertEqual(len(partner["contracts"]), 1)
        self.assertEqual(partner["contracts"][0]["cups_address"], "Example Street, Girona")
        self.assertEqual(partner["contracts"][0]["contract_url"], "https://erp.example.test/contract/5")
        self.assertFalse(partner["contracts"][0]["active"])

    def test_partner_summary_keeps_administrator_contracts_without_duplicates(self):
        self.erp_model("res.partner", records=[
            {"id": 42, "name": "Administrator"}, {"id": 43, "name": "Holder"},
        ])
        records = [
            {"id": 5, "name": "C005", "administradora": [42, "Administrator"],
             "titular": [43, "Holder"], "pagador": [43, "Holder"], "soci": [43, "Holder"]},
            {"id": 6, "name": "C006", "administradora": [42, "Administrator"],
             "titular": [42, "Administrator"], "pagador": [42, "Administrator"],
             "soci": [42, "Administrator"]},
        ]
        contracts = self.erp_model("giscedata.polissa", [5, 6], records)
        contracts.read.side_effect = lambda ids, fields: [
            {key: value for key, value in record.items() if key == "id" or key in fields}
            for record in records if record["id"] in ids
        ]

        partners = {
            partner["id"]: partner
            for partner in self.service._build_partner_summary(self.client, [42, 43], 20)
        }

        self.assertEqual([contract["contract_id"] for contract in partners[42]["contracts"]], [5, 6])
        self.assertEqual([contract["contract_id"] for contract in partners[43]["contracts"]], [5])
        self.assertIn("administradora", contracts.read.call_args.kwargs["fields"])

    def test_contract_details_validate_input_and_handle_missing_contracts(self):
        self.assertEqual(self.service.contract_details(), {"status": "ok", "contracts": {}})
        with self.assertRaises(ValidationError):
            self.service.contract_details("C005")
        self.erp_model("giscedata.polissa")
        self.assertEqual(self.service.contract_details(["missing"]), {"status": "no_info", "contracts": {}})

    def test_contract_details_include_sorted_invoices_readings_and_atr(self):
        self.erp_model("giscedata.polissa", [5], [{"id": 5, "name": "C005"}])
        invoices = self.erp_model("giscedata.facturacio.factura", [1, 2], [
            {"id": 1, "polissa_id": [5, "C005"], "date_invoice": "2026-01-01"},
            {"id": 2, "polissa_id": [5, "C005"], "date_invoice": "2026-02-01", "amount_total": 25},
        ])
        self.erp_model("giscedata.lectures.comptador", [8], [
            {"id": 8, "polissa": [5, "C005"], "lectures": [10, 11]},
        ])
        self.erp_model("giscedata.lectures.lectura", records=[
            {"comptador": [8, "Meter"], "name": "2026-01-01", "lectura": 100},
            {"comptador": [8, "Meter"], "name": "2026-02-01", "lectura": 200, "periode": [1, "P1"]},
        ])
        self.erp_model("giscedata.switching", [3, 4], [
            {"cups_polissa_id": [5, "C005"], "date": "2026-01-01"},
            {"cups_polissa_id": [5, "C005"], "date": "2026-02-01", "proces_id": [1, "C1"]},
        ])
        result = self.service.contract_details(["C005"])
        self.assertEqual(result["status"], "ok")
        details = result["contracts"]["C005"]
        self.assertEqual([i["invoice_id"] for i in details["invoices"]], [2, 1])
        self.assertEqual(details["invoices"][0]["invoice_url"], "https://erp.example.test/invoice/2")
        self.assertEqual([r["reading"] for r in details["meter_readings"]], [200, 100])
        self.assertEqual(details["atr_cases"][0]["process"], "C1")
        self.assertIn(("state", "!=", "draft"), invoices.search.call_args.args[0])

    def test_partner_action_prefers_erp_id_then_vat(self):
        partner = self.env["res.partner"].create({"name": "Lookup test", "som_erp_id": 42})
        self.assertEqual(partner.action_open_contract_lookup()["params"], {
            "field": "partner_id", "value": "42", "auto_search": True,
        })
        partner.with_context(no_vat_validation=True).write({"som_erp_id": False, "vat": "ES12345678Z"})
        self.assertEqual(partner.action_open_contract_lookup()["params"], {
            "field": "nif", "value": "12345678Z", "auto_search": True,
        })
        partner.vat = False
        self.assertFalse(partner.action_open_contract_lookup()["params"]["auto_search"])

    def test_all_search_combines_partner_and_contract_matches(self):
        self.erp_model("res.partner.address", [1], [{"partner_id": [42, "Example"]}])
        self.erp_model("res.partner", [42], [{"id": 42, "name": "Example"}])
        self.erp_model("giscedata.polissa", [5], [{
            "id": 5, "name": "C005", "titular": [42, "Example"], "pagador": [43, "Other"],
        }])
        result = self.service.search(" ALL ", " Example ", limit=1)
        self.assertTrue(result["too_many"])
        self.assertEqual(result["field"], "all")
        self.assertEqual(result["value"], "Example")
        self.assertEqual(result["count"], 1)

    def test_contract_details_without_related_records(self):
        self.erp_model("giscedata.polissa", [5], [{"id": 5, "name": "C005"}])
        for model in ("giscedata.facturacio.factura", "giscedata.lectures.comptador", "giscedata.switching"):
            self.erp_model(model)
        details = self.service.contract_details(["C005"])["contracts"]["C005"]
        self.assertEqual(details, {"invoices": [], "meter_readings": [], "atr_cases": []})

    def test_erp_connection_uses_server_configuration(self):
        config = {"erp_uri": "https://erp.example.test", "erp_port": 443,
                  "erp_dbname": "test", "erp_user": "test-user", "erp_pwd": "test-password"}
        module = "odoo.addons.helpdesk_contract_lookup.services.erp_lookup_service"
        with patch(module + ".config", config), patch(module + ".Client") as client:
            connected = self.real_get_erp_client()
            self.assertIs(connected, client.return_value)
            client.assert_called_once_with(
                server="https://erp.example.test:443", db="test", user="test-user", password="test-password",
            )
        with patch(module + ".config", {}), patch(module + ".Client") as client:
            with self.assertRaises(UserError):
                self.real_get_erp_client()
            client.assert_not_called()
