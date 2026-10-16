# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.tools import html2plaintext


def _body_to_text(html):
    """Convert HTML body to plain text, collapsing whitespace."""
    if not html:
        return ""
    text = html2plaintext(html)
    return " ".join(text.split())


class MailMessage(models.Model):
    _inherit = "mail.message"

    pct_body_preview = fields.Char(
        string="Preview",
        compute="_compute_pct_body_preview",
    )
    pct_body_text = fields.Text(
        string="Body (plain text)",
        store=True,
        compute="_compute_pct_body_text",
    )
    pct_origin_model_label = fields.Char(
        string="Origin model",
        compute="_compute_pct_origin_model_label",
    )
    pct_origin_display_name = fields.Char(
        string="Origin",
        compute="_compute_pct_origin_display_name",
    )
    pct_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        store=True,
        compute="_compute_pct_partner_id",
    )

    # Models from which we can resolve a partner_id directly.
    # res.partner is handled separately (res_id IS the partner).
    _PCT_PARTNER_MODELS = {"crm.lead", "helpdesk.ticket"}

    def _compute_pct_body_preview(self):
        for message in self:
            message.pct_body_preview = _body_to_text(message.body)[:240]

    @api.depends("body")
    def _compute_pct_body_text(self):
        for message in self:
            message.pct_body_text = _body_to_text(message.body)

    def _compute_pct_origin_model_label(self):
        model_names = {name for name in self.mapped("model") if name}
        model_labels = {}
        if model_names:
            for model_record in self.env["ir.model"].sudo().search(
                [("model", "in", list(model_names))]
            ):
                model_labels[model_record.model] = model_record.name

        for message in self:
            message.pct_origin_model_label = model_labels.get(
                message.model, message.model or ""
            )

    def _compute_pct_origin_display_name(self):
        for message in self:
            message.pct_origin_display_name = message.record_name or ""

    @api.depends("model", "res_id")
    def _compute_pct_partner_id(self):
        partner_model = self.env["res.partner"]
        # Group messages by model to avoid per-record queries.
        by_model = {}
        for message in self:
            if message.model and message.res_id:
                by_model.setdefault(message.model, []).append(message)

        for model_name, messages in by_model.items():
            if model_name == "res.partner":
                for message in messages:
                    message.pct_partner_id = partner_model.browse(message.res_id).exists()
            elif model_name in self._PCT_PARTNER_MODELS:
                res_ids = [m.res_id for m in messages]
                records = self.env[model_name].sudo().browse(res_ids).exists()
                by_id = {r.id: r.partner_id for r in records}
                for message in messages:
                    message.pct_partner_id = by_id.get(message.res_id, False)
            else:
                for message in messages:
                    message.pct_partner_id = False

        # Messages without model/res_id get an empty value.
        for message in self:
            if not message.model or not message.res_id:
                message.pct_partner_id = False

    def action_pct_open_related_record(self):
        self.ensure_one()
        if not self.model or not self.res_id:
            return self._pct_display_no_related_record_notification()

        try:
            record = self.env[self.model].browse(self.res_id).exists()
            if record:
                record.check_access_rights("read")
                record.check_access_rule("read")
        except (AccessError, KeyError):
            record = self.env[self._name].browse()

        if not record:
            return self._pct_display_no_related_record_notification()

        return {
            "type": "ir.actions.act_window",
            "name": record.display_name,
            "res_model": self.model,
            "res_id": record.id,
            "view_mode": "form",
            "target": "current",
        }

    def _pct_display_no_related_record_notification(self):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("No related document"),
                "message": _("This message is not linked to an available document."),
                "type": "warning",
                "sticky": False,
            },
        }
