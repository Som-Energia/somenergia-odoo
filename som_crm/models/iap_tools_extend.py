# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SomCrmMailDomainBlacklist(models.Model):
    _name = 'som.crm.mail.domain.blacklist'
    _description = 'Mail Domain Blacklist'

    name = fields.Char(string='Domain', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def _update_blacklist(self):
        try:
            from odoo.addons.iap.tools.iap_tools import _MAIL_DOMAIN_BLACKLIST
            if isinstance(_MAIL_DOMAIN_BLACKLIST, set):
                _MAIL_DOMAIN_BLACKLIST.update(self.search([]).mapped('name'))
        except ImportError:
            pass

    def _register_hook(self):
        super()._register_hook()
        self._update_blacklist()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_blacklist()
        return records
