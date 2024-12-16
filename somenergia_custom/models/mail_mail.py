# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MailMail(models.Model):
    _inherit = "mail.mail"

    @api.model_create_multi
    def create(self, vals_list):
        try:
            ctx = self.env.context
            if ctx.get('som_from_ticket') and ctx.get('som_id_support_partner') and ctx.get('som_mail_from'):
                recipient_ids = vals_list[0].get("recipient_ids")
                if recipient_ids[0][1] == ctx.get('som_id_support_partner'):
                    vals_list[0].update({"email_from": ctx.get('som_mail_from')})
        except Exception as e:
            pass
        return super(MailMail, self).create(vals_list)
