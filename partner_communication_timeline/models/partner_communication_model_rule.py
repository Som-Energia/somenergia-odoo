# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PartnerCommunicationModelRule(models.Model):
    _name = "partner.communication.model.rule"
    _description = "Partner Communication Timeline Rule"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    model_id = fields.Many2one(
        "ir.model",
        required=True,
        ondelete="cascade",
        domain=[("transient", "=", False)],
        string="Model",
    )
    model_name = fields.Char(related="model_id.model", store=True, readonly=True)
    partner_field_name = fields.Char(
        required=True,
        default="partner_id",
        string="Partner field",
        help="Name of the Many2one field pointing to res.partner on the selected model.",
    )
    include_child_contacts = fields.Boolean(
        default=True,
        help=(
            "When enabled, a company contact also includes documents linked to its "
            "child contacts."
        ),
    )
    description = fields.Text()

    _sql_constraints = [
        (
            "unique_model_partner_field",
            "unique(model_id, partner_field_name)",
            "There is already a communication timeline rule for this model and partner field.",
        )
    ]

    @api.constrains("model_id", "partner_field_name")
    def _check_partner_field_name(self):
        for rule in self:
            if not rule.model_id or not rule.partner_field_name:
                continue
            try:
                model = self.env[rule.model_id.model]
            except KeyError as exc:
                raise ValidationError(
                    _("The selected model is not available in the registry.")
                ) from exc

            field = model._fields.get(rule.partner_field_name)
            if not field:
                raise ValidationError(
                    _("Field '%s' does not exist on model '%s'.")
                    % (rule.partner_field_name, rule.model_id.model)
                )
            if field.type != "many2one" or field.comodel_name != "res.partner":
                raise ValidationError(
                    _("Field '%s' on model '%s' must be a Many2one to Contacts.")
                    % (rule.partner_field_name, rule.model_id.model)
                )
