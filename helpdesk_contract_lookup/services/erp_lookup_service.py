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
        "partner_id",
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

    def _address_ids_by_phone(self, client, phone):
        return self._execute_kw(
            client,
            "res.partner.address",
            "search",
            [["|", ("phone", "like", phone), ("mobile", "like", phone)]],
        )

    def _address_ids_by_email(self, client, email):
        return self._execute_kw(
            client,
            "res.partner.address",
            "search",
            [[("email", "ilike", email)]],
        )

    def _partner_ids_by_address_ids(self, client, address_ids):
        if not address_ids:
            return []
        addresses = self._execute_kw(
            client,
            "res.partner.address",
            "read",
            [address_ids],
            {"fields": ["partner_id"]},
        )
        return [a["partner_id"][0] for a in addresses if a.get("partner_id")]

    def _search_partner_ids(self, client, field, value, limit):
        if field == "phone":
            address_ids = self._address_ids_by_phone(client, value)
            return self._partner_ids_by_address_ids(client, address_ids)

        if field == "email":
            address_ids = self._address_ids_by_email(client, value)
            return self._partner_ids_by_address_ids(client, address_ids)

        if field == "partner_id":
            try:
                pid = int(value)
            except (TypeError, ValueError):
                raise ValidationError(_("partner_id must be a numeric value."))
            return self._execute_kw(
                client, "res.partner", "search",
                [[("id", "=", pid)]],
            )

        partner_domain_by_field = {
            "name": [("name", "ilike", value)],
            "nif": [("vat", "ilike", value)],
            "soci": [("ref", "ilike", value)],
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
            address_ids = self._address_ids_by_phone(client, value)
            address_ids += self._address_ids_by_email(client, value)
            partner_ids = set(self._partner_ids_by_address_ids(client, address_ids))
            partner_ids.update(self._execute_kw(
                client,
                "res.partner",
                "search",
                [["|", "|", "|",
                    ("name", "ilike", value),
                    ("vat", "ilike", value),
                    ("ref", "ilike", value),
                    ("email", "ilike", value),
                ]],
                {"limit": limit},
            ))
            return list(partner_ids)

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
                    "lang",
                    "comment",
                    "www_email",
                    "www_phone",
                    "www_mobile",
                    "www_street",
                    "www_municipi",
                    "www_zip",
                    "www_provincia",
                    "empowering_token",
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
                    "email": partner.get("www_email") or "",
                    "phones": [x for x in [partner.get("www_phone"), partner.get("www_mobile")] if x],
                    "address": partner.get("www_street") or "",
                    "city": (partner.get("www_municipi") or [False, {}])[1].get("name", "") if partner.get("www_municipi") else "",
                    "postalcode": partner.get("www_zip") or "",
                    "state": (partner.get("www_provincia") or [False, {}])[1].get("name", "") if partner.get("www_provincia") else "",
                    "ov": bool(partner.get("empowering_token")),
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

        # Build result indexed by contract id for efficient lookup
        result_by_id = {}
        result = {}
        for contract in contracts:
            contract_name = contract.get("name")
            result[contract_name] = {
                "invoices": [],
                "atr_cases": [],
                "meter_readings": [],
            }
            result_by_id[contract["id"]] = result[contract_name]

        self._fetch_invoices(client, contract_ids, result_by_id)
        self._fetch_meter_readings(client, contract_ids, result_by_id)
        self._fetch_atr_cases(client, contract_ids, result_by_id)

        return {"status": "ok", "contracts": result}

    def _fetch_invoices(self, client, contract_ids, result_by_id):
        """Fetch invoices for the given contract ids and populate result_by_id buckets."""
        # Use search + read (two steps) instead of search_reader:
        # search_reader builds raw SQL and cannot resolve functional fields like 'number'.
        invoice_ids = self._execute_kw(
            client,
            "giscedata.facturacio.factura",
            "search",
            [[
                ("polissa_id", "in", contract_ids),
                ("state", "!=", "draft"),
                ("type", "in", ["out_invoice", "out_refund"]),
            ]],
            {"context": {"active_test": False}},
        )
        if not invoice_ids:
            return
        invoices = self._execute_kw(
            client,
            "giscedata.facturacio.factura",
            "read",
            [invoice_ids],
            {"fields": [
                "number",
                "data_inici",
                "data_final",
                "amount_total",
                "energia_kwh",
                "dies",
                "date_invoice",
                "date_due",
                "state",
                "polissa_id",
            ]},
        )
        for invoice in invoices:
            polissa = invoice.get("polissa_id")
            contract_id = polissa[0] if polissa else None
            bucket = result_by_id.get(contract_id)
            if bucket is not None:
                bucket["invoices"].append({
                    "number": invoice.get("number") or "",
                    "initial_date": invoice.get("data_inici"),
                    "final_date": invoice.get("data_final"),
                    "invoice_date": invoice.get("date_invoice"),
                    "due_date": invoice.get("date_due"),
                    "amount": invoice.get("amount_total"),
                    "energy_kwh": invoice.get("energia_kwh") or 0,
                    "days": invoice.get("dies"),
                    "state": invoice.get("state"),
                })
        for bucket in result_by_id.values():
            bucket["invoices"].sort(key=lambda x: x.get("invoice_date") or "", reverse=True)

    def _fetch_meter_readings(self, client, contract_ids, result_by_id, limit=12):
        """Fetch meter readings for the given contract ids and populate result_by_id buckets."""
        meter_ids = self._execute_kw(
            client,
            "giscedata.lectures.comptador",
            "search",
            [[("polissa", "in", contract_ids), ("active", "=", True)]],
            {},
        )
        if not meter_ids:
            return

        meters = self._execute_kw(
            client,
            "giscedata.lectures.comptador",
            "read",
            [meter_ids],
            {"fields": ["lectures", "name", "polissa"]},
        )

        meter2contract = {
            meter["id"]: meter["polissa"][0]
            for meter in meters
            if meter.get("polissa")
        }

        reading_ids = []
        for meter in meters:
            meter_readings = meter.get("lectures") or []
            reading_ids.extend(meter_readings[:limit])

        if not reading_ids:
            return

        readings = self._execute_kw(
            client,
            "giscedata.lectures.lectura",
            "read",
            [reading_ids],
            {"fields": ["name", "lectura", "origen_id", "periode", "comptador"]},
        )

        for reading in readings:
            comptador = reading.get("comptador")
            if not comptador:
                continue
            contract_id = meter2contract.get(comptador[0])
            bucket = result_by_id.get(contract_id)
            if bucket is not None:
                periode = reading.get("periode")
                origen = reading.get("origen_id")
                bucket["meter_readings"].append({
                    "meter": comptador[1],
                    "date": reading.get("name"),
                    "period": periode[1] if periode else "",
                    "reading": reading.get("lectura"),
                    "origin": origen[1] if origen else "",
                })

        for bucket in result_by_id.values():
            bucket["meter_readings"].sort(key=lambda x: x.get("date") or "", reverse=True)

    def _fetch_atr_cases(self, client, contract_ids, result_by_id):
        """Fetch ATR switching cases for the given contract ids and populate result_by_id buckets."""
        case_ids = self._execute_kw(
            client,
            "giscedata.switching",
            "search",
            [[("cups_polissa_id", "in", contract_ids)]],
            {},
        )
        if not case_ids:
            return
        cases = self._execute_kw(
            client,
            "giscedata.switching",
            "read",
            [case_ids],
            {"fields": ["date", "proces_id", "step_id", "state", "additional_info", "cups_polissa_id"]},
        )
        for case in cases:
            polissa = case.get("cups_polissa_id")
            contract_id = polissa[0] if polissa else None
            bucket = result_by_id.get(contract_id)
            if bucket is not None:
                bucket["atr_cases"].append({
                    "date": case.get("date"),
                    "process": (case.get("proces_id") or [False, ""])[1],
                    "step": (case.get("step_id") or [False, ""])[1],
                    "state": case.get("state") or "",
                    "additional_info": case.get("additional_info") or "",
                })
        for bucket in result_by_id.values():
            bucket["atr_cases"].sort(key=lambda x: x.get("date") or "", reverse=True)
