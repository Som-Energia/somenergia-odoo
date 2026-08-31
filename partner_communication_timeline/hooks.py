# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api


DEFAULT_RULES = (
    ("crm.lead", "partner_id", "CRM Leads and Opportunities", 10),
    ("helpdesk.ticket", "partner_id", "Helpdesk Tickets", 20),
)


def _is_valid_partner_field(env, model_name, field_name):
    try:
        model = env[model_name]
    except KeyError:
        return False
    field = model._fields.get(field_name)
    return bool(
        field
        and field.type == "many2one"
        and getattr(field, "comodel_name", None) == "res.partner"
    )


def post_init_hook(cr, registry):
    """Create default aggregation rules when the target modules are installed."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    rule_model = env["partner.communication.model.rule"]
    ir_model = env["ir.model"]

    for model_name, field_name, rule_name, sequence in DEFAULT_RULES:
        model_record = ir_model.search([("model", "=", model_name)], limit=1)
        if not model_record or not _is_valid_partner_field(env, model_name, field_name):
            continue

        existing = rule_model.search(
            [
                ("model_id", "=", model_record.id),
                ("partner_field_name", "=", field_name),
            ],
            limit=1,
        )
        if existing:
            continue

        rule_model.create(
            {
                "name": rule_name,
                "sequence": sequence,
                "model_id": model_record.id,
                "partner_field_name": field_name,
                "include_child_contacts": True,
            }
        )
