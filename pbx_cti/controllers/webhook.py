# -*- coding: utf-8 -*-
import json
import logging
import re

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

BUS_CHANNEL_PREFIX = "pbx_cti_"
BUS_MESSAGE_TYPE = "pbx_incoming_call"


def _clean_phone(phone):
    """Strip +34/0034 prefix and keep digits only."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0034"):
        digits = digits[4:]
    elif digits.startswith("34") and len(digits) > 9:
        digits = digits[2:]
    return digits


class PbxCtiWebhook(http.Controller):

    @http.route(
        "/pbx/ringring",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def ringring(self, **post):
        # --- 1. Authenticate via API key ---
        api_key = post.get("apikey") or request.httprequest.headers.get("X-PBX-Api-Key")
        expected_key = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("pbx_cti.api_key")
        )
        if not expected_key or api_key != expected_key:
            _logger.warning("pbx_cti: invalid or missing API key from %s", request.httprequest.remote_addr)
            return request.make_response(
                json.dumps({"error": "unauthorized"}),
                headers=[("Content-Type", "application/json")],
                status=401,
            )

        # --- 2. Parse params ---
        phone_raw = post.get("phone", "")
        extension = post.get("extension") or post.get("ext", "")
        callid = post.get("callid", "")
        phone = _clean_phone(phone_raw)

        if not phone or not extension:
            _logger.warning("pbx_cti: missing phone or extension — phone=%r ext=%r", phone_raw, extension)
            return request.make_response(
                json.dumps({"error": "missing_params", "detail": "phone and extension are required"}),
                headers=[("Content-Type", "application/json")],
                status=400,
            )

        _logger.info("pbx_cti: incoming call phone=%s extension=%s callid=%s", phone, extension, callid)

        # --- 3. Resolve extension → user ---
        user = request.env["res.users"].sudo().search(
            [("pbx_extension", "=", extension)], limit=1
        )
        if not user:
            _logger.warning("pbx_cti: no user found for extension %s", extension)
            return request.make_response(
                json.dumps({"result": "no_user", "extension": extension}),
                headers=[("Content-Type", "application/json")],
            )

        # --- 4. Resolve phone → partner ---
        partner = request.env["res.partner"].sudo().search(
            ["|", ("phone", "=", phone), ("mobile", "=", phone)],
            limit=1,
        )
        if not partner:
            _logger.info("pbx_cti: no partner found for phone %s (user %s)", phone, user.login)
            return request.make_response(
                json.dumps({"result": "no_partner", "phone": phone}),
                headers=[("Content-Type", "application/json")],
            )

        # --- 5. Push to user's browser via bus.bus ---
        channel = "{}{}".format(BUS_CHANNEL_PREFIX, user.id)
        request.env["bus.bus"].sudo()._sendone(
            channel,
            BUS_MESSAGE_TYPE,
            {
                "res_model": "res.partner",
                "res_id": partner.id,
                "phone": phone,
                "callid": callid,
            },
        )
        _logger.info(
            "pbx_cti: pushed to channel %s → partner %s (%s)",
            channel, partner.name, partner.id,
        )

        return request.make_response(
            json.dumps({"result": "ok", "partner_id": partner.id, "partner_name": partner.name}),
            headers=[("Content-Type", "application/json")],
        )
