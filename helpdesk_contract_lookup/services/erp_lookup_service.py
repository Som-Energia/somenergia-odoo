import logging

from erppeek import Client

from odoo import _, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config


_logger = logging.getLogger(__name__)


class HelpdeskContractLookupService(models.AbstractModel):
    _name = "helpdesk.contract.lookup.service"
    _description = "Helpdesk Contract Lookup Service"

    _ALLOWED_FIELDS = {
        "phone",
        "name",
        "nif",
        "soci",
        "email",
        "contract",
        "cups",
        "all",
    }

    def _get_param(self, key, default=False):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def _get_search_limit(self, provided_limit):
        if provided_limit:
            try:
                return max(1, int(provided_limit))
            except (TypeError, ValueError):
                raise ValidationError(_("Invalid search limit."))
        default_limit = self._get_param("helpdesk_contract_lookup.search_limit", "20")
        try:
            return max(1, int(default_limit))
        except (TypeError, ValueError):
            return 20

    def _get_erp_client(self):
        server = "%s:%s" % (config.get("erp_uri"), config.get("erp_port"))
        db = config.get("erp_dbname")
        username = config.get("erp_user")
        password = config.get("erp_pwd")

        if not all([server, db, username, password]):
            raise UserError(
                _(
                    "ERP connection is not configured. "
                    "Please set erp_uri, erp_port, erp_dbname, erp_user and erp_pwd in Odoo server config."
                )
            )

        try:
            client = Client(
                server=server,
                db=db,
                user=username,
                password=password,
            )
        except Exception as exc:
            _logger.exception("Error connecting to ERP")
            raise UserError(_("Could not connect to ERP: %s") % exc)

        return client

    def _execute_kw(self, client, model, method, args=None, kwargs=None):
        args = args or []
        kwargs = kwargs or {}
        erp_model = client.model(model)
        return getattr(erp_model, method)(*args, **kwargs)

    def _search_partner_ids(self, client, field, value, limit):
        partner_domain_by_field = {
            "name": [("name", "ilike", value)],
            "nif": [("vat", "ilike", value)],
            "soci": [("ref", "ilike", value)],
            "email": [("email", "ilike", value)],
            "phone": ["|", ("phone", "ilike", value), ("mobile", "ilike", value)],
        }
        if field in partner_domain_by_field:
            return self._execute_kw(
                client,
                "res.partner",
                "search",
                [partner_domain_by_field[field]],
                {"limit": limit},
            )

        if field == "all":
            return self._execute_kw(
                client,
                "res.partner",
                "search",
                [["|", "|", "|", ("name", "ilike", value), ("vat", "ilike", value), ("ref", "ilike", value), ("email", "ilike", value)]],
                {"limit": limit},
            )

        return []

    def _search_contract_partner_ids(self, client, field, value, limit):
        if field not in {"contract", "cups", "all"}:
            return []

        if field == "contract":
            domain = [("name", "=", value)]
        elif field == "cups":
            domain = [("cups.name", "ilike", value[:20])]
        else:
            domain = ["|", ("name", "ilike", value), ("cups.name", "ilike", value[:20])]

        contract_ids = self._execute_kw(
            client,
            "giscedata.polissa",
            "search",
            [domain],
            {"limit": limit, "context": {"active_test": False}},
        )
        if not contract_ids:
            return []

        contracts = self._execute_kw(
            client,
            "giscedata.polissa",
            "read",
            [contract_ids],
            {"fields": ["titular", "pagador", "soci"]},
        )
        partner_ids = set()
        for contract in contracts:
            for field_name in ["titular", "pagador", "soci"]:
                value = contract.get(field_name)
                if value and value[0]:
                    partner_ids.add(value[0])
        return list(partner_ids)

    def _build_partner_summary(self, client, partner_ids, limit):
        if not partner_ids:
            return []

        partner_ids = partner_ids[:limit]
        partners = self._execute_kw(
            client,
            "res.partner",
            "read",
            [partner_ids],
            {
                "fields": [
                    "name",
                    "ref",
                    "vat",
                    "email",
                    "phone",
                    "mobile",
                    "lang",
                    "comment",
                ]
            },
        )

        contract_ids = self._execute_kw(
            client,
            "giscedata.polissa",
            "search",
            [["|", "|", "|", ("titular", "in", partner_ids), ("administradora", "in", partner_ids), ("pagador", "in", partner_ids), ("soci", "in", partner_ids)]],
            {"context": {"active_test": False}},
        )
        contracts = []
        if contract_ids:
            contracts = self._execute_kw(
                client,
                "giscedata.polissa",
                "read",
                [contract_ids],
                {
                    "fields": [
                        "name",
                        "state",
                        "active",
                        "cups",
                        "titular",
                        "pagador",
                        "soci",
                    ]
                },
            )

        partner_contracts = {partner_id: {} for partner_id in partner_ids}
        for contract in contracts:
            contract_number = contract.get("name")
            contract_data = {
                "number": contract_number,
                "state": contract.get("state"),
                "active": contract.get("active"),
                "cups": (contract.get("cups") or [False, ""])[1],
            }
            for rel_field in ["titular", "pagador", "soci"]:
                rel_value = contract.get(rel_field)
                if rel_value and rel_value[0] in partner_contracts:
                    partner_contracts[rel_value[0]][contract_number] = contract_data

        result = []
        for partner in partners:
            partner_id = partner["id"]
            result.append(
                {
                    "id": partner_id,
                    "name": partner.get("name"),
                    "member_code": partner.get("ref") or "",
                    "vat": partner.get("vat") or "",
                    "email": partner.get("email") or "",
                    "phones": [x for x in [partner.get("phone"), partner.get("mobile")] if x],
                    "lang": partner.get("lang") or "",
                    "comment": partner.get("comment") or "",
                    "contracts": sorted(
                        partner_contracts.get(partner_id, {}).values(),
                        key=lambda item: item.get("number") or "",
                    ),
                }
            )
        return result

    def search(self, field="phone", value="", limit=20):
        field = (field or "phone").strip().lower()
        value = (value or "").strip()

        if field not in self._ALLOWED_FIELDS:
            raise ValidationError(_("Unsupported search field: %s") % field)
        if not value:
            raise ValidationError(_("A search value is required."))

        parsed_limit = self._get_search_limit(limit)
        client = self._get_erp_client()

        partner_ids = set(self._search_partner_ids(client, field, value, parsed_limit))
        partner_ids.update(self._search_contract_partner_ids(client, field, value, parsed_limit))
        partner_ids = list(partner_ids)

        too_many = len(partner_ids) > parsed_limit
        partners = self._build_partner_summary(client, partner_ids, parsed_limit)

        return {
            "status": "ok" if partners else "no_info",
            "field": field,
            "value": value,
            "limit": parsed_limit,
            "count": len(partners),
            "too_many": too_many,
            "partners": partners,
        }

    def contract_details(self, contract_numbers=None):
        contract_numbers = contract_numbers or []
        if not isinstance(contract_numbers, list):
            raise ValidationError(_("contract_numbers must be a list."))
        if not contract_numbers:
            return {"status": "ok", "contracts": {}}

        client = self._get_erp_client()

        contract_ids = self._execute_kw(
            client,
            "giscedata.polissa",
            "search",
            [[("name", "in", contract_numbers)]],
            {"context": {"active_test": False}},
        )

        if not contract_ids:
            return {"status": "no_info", "contracts": {}}

        contracts = self._execute_kw(
            client,
            "giscedata.polissa",
            "read",
            [contract_ids],
            {"fields": ["name"]},
        )

        result = {}
        for contract in contracts:
            result[contract.get("name")] = {
                "invoices": [],
                "atr_cases": [],
                "meter_readings": [],
            }

        invoices = self._execute_kw(
            client,
            "giscedata.facturacio.factura",
            "search_reader",
            [
                [("polissa_id", "in", contract_ids), ("state", "!=", "draft")],
                [
                    "number",
                    "date_invoice",
                    "date_due",
                    "amount_total",
                    "state",
                    "polissa_id",
                ],
                0,
                200,
                None,
                {"active_test": False},
            ],
        )
        for invoice in invoices:
            contract_name = (invoice.get("polissa_id") or [False, ""])[1]
            if contract_name in result:
                result[contract_name]["invoices"].append(
                    {
                        "number": invoice.get("number") or "",
                        "invoice_date": invoice.get("date_invoice"),
                        "due_date": invoice.get("date_due"),
                        "amount": invoice.get("amount_total"),
                        "state": invoice.get("state"),
                    }
                )

        return {"status": "ok", "contracts": result}
