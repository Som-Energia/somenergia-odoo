# Copyright 2026 Som Energia
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

from odoo import _, fields, models
from odoo.exceptions import AccessError
from odoo.osv import expression


DEFAULT_RULE_SPECS = (
    ("crm.lead", "partner_id", True),
    ("helpdesk.ticket", "partner_id", True),
)

VISIBLE_MESSAGE_TYPES = ["email", "comment"]


class ResPartner(models.Model):
    _inherit = "res.partner"

    pct_communication_message_count = fields.Integer(
        string="Communications",
        compute="_compute_pct_communication_message_count",
    )
    pct_communication_preview_message_ids = fields.Many2many(
        comodel_name="mail.message",
        string="Latest communications",
        compute="_compute_pct_communication_preview_message_ids",
    )

    def _compute_pct_communication_message_count(self):
        message_model = self.env["mail.message"]
        for partner in self:
            if not partner.id:
                partner.pct_communication_message_count = 0
                continue
            partner.pct_communication_message_count = message_model.search_count(
                partner._pct_get_communication_message_domain()
            )

    def _compute_pct_communication_preview_message_ids(self):
        message_model = self.env["mail.message"]
        for partner in self:
            if not partner.id:
                partner.pct_communication_preview_message_ids = message_model.browse()
                continue
            partner.pct_communication_preview_message_ids = message_model.search(
                partner._pct_get_communication_message_domain(),
                order="date desc, id desc",
                limit=50,
            )

    def action_pct_open_partner_communications(self):
        self.ensure_one()
        tree_view = self.env.ref(
            "partner_communication_timeline.view_mail_message_partner_timeline_tree"
        )
        form_view = self.env.ref(
            "partner_communication_timeline.view_mail_message_partner_timeline_form"
        )
        search_view = self.env.ref(
            "partner_communication_timeline.view_mail_message_partner_timeline_search"
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Comunicacions - %s") % self.display_name,
            "res_model": "mail.message",
            "view_mode": "tree,form",
            "views": [(tree_view.id, "tree"), (form_view.id, "form")],
            "search_view_id": (search_view.id, "search"),
            "domain": self._pct_get_communication_message_domain(),
            "context": {
                "create": False,
                "edit": False,
                "delete": False,
                "default_model": "res.partner",
                "default_res_id": self.id,
            },
        }

    def _pct_get_communication_message_domain(self):
        self.ensure_one()
        partner_ids = self._pct_get_partner_scope_ids(include_children=True)
        if not partner_ids:
            return [("id", "=", 0)]

        fragments = [
            [("model", "=", "res.partner"), ("res_id", "in", partner_ids)],
            [("author_id", "in", partner_ids)],
            [("partner_ids", "in", partner_ids)],
        ]

        fragments.extend(self._pct_get_email_from_domains(partner_ids))

        for spec in self._pct_get_rule_specs():
            record_ids = self._pct_get_related_record_ids_for_rule(spec)
            if record_ids:
                fragments.append(
                    [
                        ("model", "=", spec["model"]),
                        ("res_id", "in", record_ids),
                    ]
                )

        domain = expression.OR(fragments) if fragments else [("id", "=", 0)]
        domain = expression.AND([domain, [("message_type", "in", VISIBLE_MESSAGE_TYPES)]])
        return domain

    def _pct_get_partner_scope_ids(self, include_children=True):
        self.ensure_one()
        if not self.id:
            return []
        if not include_children:
            return [self.id]

        root_partner = self.commercial_partner_id or self
        if not root_partner.id:
            root_partner = self
        return self.env["res.partner"].with_context(active_test=False).search(
            [("id", "child_of", root_partner.id)]
        ).ids

    def _pct_get_rule_specs(self):
        self.ensure_one()
        specs = []
        seen = set()
        rule_model = self.env["partner.communication.model.rule"].sudo()
        rules = rule_model.search([("active", "=", True)], order="sequence, id")

        for rule in rules:
            model_name = rule.model_name
            field_name = rule.partner_field_name
            key = (model_name, field_name)
            if key in seen:
                continue
            if not self._pct_is_valid_partner_rule(model_name, field_name):
                continue
            specs.append(
                {
                    "model": model_name,
                    "partner_field": field_name,
                    "include_child_contacts": rule.include_child_contacts,
                }
            )
            seen.add(key)

        for model_name, field_name, include_child_contacts in DEFAULT_RULE_SPECS:
            key = (model_name, field_name)
            if key in seen:
                continue
            if not self._pct_is_valid_partner_rule(model_name, field_name):
                continue
            specs.append(
                {
                    "model": model_name,
                    "partner_field": field_name,
                    "include_child_contacts": include_child_contacts,
                }
            )
            seen.add(key)

        return specs

    def _pct_is_valid_partner_rule(self, model_name, field_name):
        try:
            model = self.env[model_name]
        except KeyError:
            return False
        field = model._fields.get(field_name)
        return bool(
            field
            and field.type == "many2one"
            and getattr(field, "comodel_name", None) == "res.partner"
        )

    def _pct_get_related_record_ids_for_rule(self, spec):
        model_name = spec["model"]
        partner_field = spec["partner_field"]
        include_children = spec.get("include_child_contacts", True)
        partner_ids = self._pct_get_partner_scope_ids(include_children=include_children)
        if not partner_ids:
            return []

        try:
            target_model = self.env[model_name].with_context(active_test=False)
            target_model.check_access_rights("read")
            records = target_model.search([(partner_field, "in", partner_ids)])
        except AccessError:
            return []
        return records.ids

    def _pct_get_email_from_domains(self, partner_ids):
        partners = self.env["res.partner"].browse(partner_ids)
        emails = set()
        has_email_normalized = "email_normalized" in partners._fields
        for partner in partners:
            email = partner.email or ""
            email_normalized = partner.email_normalized if has_email_normalized else ""
            for candidate in (email_normalized, email):
                candidate = (candidate or "").strip().lower()
                if candidate:
                    emails.add(candidate)

        return [
            [("message_type", "=", "email"), ("email_from", "ilike", email)]
            for email in sorted(emails)
        ]
