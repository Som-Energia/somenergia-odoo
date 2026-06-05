import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError, ValidationError


_logger = logging.getLogger(__name__)
_HELPDESK_GROUP = "helpdesk_mgmt.group_helpdesk_user"


class HelpdeskContractLookupController(http.Controller):
    def _check_access(self):
        user = request.env.user
        if not user.has_group(_HELPDESK_GROUP):
            raise AccessError("You do not have access to Contract Lookup.")

    def _get_or_create_odoo_partner(self, partner_id, partner_name, partner_vat):
        partner_model = request.env["res.partner"]
        odoo_partner = None

        if "som_erp_id" in partner_model.sudo()._fields:
            odoo_partner = partner_model.sudo().search(
                [("som_erp_id", "=", partner_id)], limit=1
            )
            if not odoo_partner:
                odoo_partner = partner_model.sudo().create({
                    "name": partner_name,
                    "vat": partner_vat,
                    "som_erp_id": partner_id,
                    "type": "contact",
                })
                _logger.info(
                    "Created new Odoo partner %s from ERP id %s",
                    odoo_partner.id, partner_id,
                )
            else:
                _logger.info(
                    "Found existing Odoo partner %s for ERP id %s",
                    odoo_partner.id, partner_id,
                )
        else:
            _logger.warning(
                "som_erp_id field not found on res.partner, skipping Odoo partner link"
            )

        return odoo_partner

    @http.route(
        "/helpdesk_contract_lookup/search",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def search(self, field="phone", value="", limit=20):
        self._check_access()
        try:
            return request.env["helpdesk.contract.lookup.service"].search(
                field=field,
                value=value,
                limit=limit,
            )
        except (ValidationError, UserError, AccessError):
            raise
        except Exception as exc:
            _logger.exception("Unexpected error during search")
            raise UserError("Unexpected error while searching contracts: %s" % exc)

    @http.route(
        "/helpdesk_contract_lookup/contract_details",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def contract_details(self, contract_numbers=None):
        self._check_access()
        contract_numbers = contract_numbers or []
        try:
            return request.env["helpdesk.contract.lookup.service"].contract_details(
                contract_numbers=contract_numbers
            )
        except (ValidationError, UserError, AccessError):
            raise
        except Exception as exc:
            _logger.exception("Unexpected error during contract details")
            raise UserError("Unexpected error while fetching contract details: %s" % exc)

    @http.route(
        "/helpdesk_contract_lookup/link_partner_to_call",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def link_partner_to_call(
            self, phonecall_id=None, partner_id=None, partner_name=None, partner_vat=None):
        self._check_access()
        if not phonecall_id or not partner_id:
            raise ValidationError("phonecall_id and partner_id are required.")
        phonecall = request.env["crm.phonecall"].sudo().browse(phonecall_id)
        if not phonecall.exists():
            raise ValidationError("Phone call record not found.")

        odoo_partner = self._get_or_create_odoo_partner(partner_id, partner_name, partner_vat)

        phonecall.write({
            "som_caller_erp_id": partner_id,
            "som_caller_name": partner_name or False,
            "som_caller_vat": partner_vat or False,
            "partner_id": odoo_partner.id if odoo_partner else False,
        })
        return {"status": "ok"}

    @http.route(
        "/helpdesk_contract_lookup/open_partner_in_odoo",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def open_partner_in_odoo(self, partner_id=None, partner_name=None, partner_vat=None):
        self._check_access()
        if not partner_id:
            raise ValidationError("partner_id is required.")

        odoo_partner = self._get_or_create_odoo_partner(partner_id, partner_name, partner_vat)
        if not odoo_partner:
            raise UserError("Could not resolve Odoo partner.")

        return {"status": "ok", "odoo_partner_id": odoo_partner.id}
