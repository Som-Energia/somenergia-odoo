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
        phonecall.write({
            "som_caller_erp_id": partner_id,
            "som_caller_name": partner_name or False,
            "som_caller_vat": partner_vat or False,
        })
        return {"status": "ok"}
