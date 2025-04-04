# -*- coding: utf-8 -*-

from odoo import _, fields, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        if self._name == 'helpdesk.ticket' and self.team_id.som_support_partner_id and self.team_id.alias_id:
            mail_from = '"%s" <%s>'%(self.team_id.name, self.team_id.alias_id.display_name)
            return super(
                MailThread, self.with_context(
                    som_from_ticket=True,
                    som_id_support_partner= self.team_id.som_support_partner_id.id,
                    som_mail_from=mail_from)
            )._notify_thread(message, msg_vals=msg_vals, mail_auto_delete=False, **kwargs)
        else:
            return super(MailThread, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
