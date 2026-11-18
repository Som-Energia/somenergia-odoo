from odoo import api, models
from odoo.tools.misc import clean_context

from .mail_message import HAS_NATIVE_AUTO_COMMENT


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_track_post_template(self, changes):
        if HAS_NATIVE_AUTO_COMMENT:
            return super()._message_track_post_template(changes)
        if not changes:
            return True

        # Mirror the pinned core dispatch with upstream 16.0's extra default.
        # Applying this after _track_template also covers templates returned by
        # other addons, regardless of their position in the inheritance chain.
        self = self.with_context(clean_context(self._context))
        for template, options in self._track_template(changes).values():
            if not template:
                continue
            options = dict(options)
            options.setdefault("message_type", "auto_comment")
            if isinstance(template, str):
                self._fallback_lang().message_post_with_view(template, **options)
            else:
                self._fallback_lang().message_post_with_template(template.id, **options)
        return True

    @api.model
    def message_parse(self, message, save_original=False):
        values = super().message_parse(message, save_original=save_original)
        if not HAS_NATIVE_AUTO_COMMENT and values.get("parent_id"):
            parent = self.env["mail.message"].browse(values["parent_id"])
            if parent.message_type == "auto_comment":
                values["is_internal"] = False
        return values
