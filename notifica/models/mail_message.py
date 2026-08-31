# -*- coding: utf-8 -*-
from odoo import models, fields


class MailMessage(models.Model):
    _inherit = 'mail.message'

    is_external_log = fields.Boolean(
        string='Is External Log',
        default=False,
        index=True,
    )
