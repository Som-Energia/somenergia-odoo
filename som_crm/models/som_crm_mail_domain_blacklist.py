# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons.iap.tools.iap_tools import _MAIL_DOMAIN_BLACKLIST


class SomCrmMailDomainBlacklist(models.Model):
    _name = 'som.crm.mail.domain.blacklist'
    _description = 'Mail Domain Blacklist'

    name = fields.Char(string='Domain', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    def _update_blacklist_rebuild(self):
        try:
            if isinstance(_MAIL_DOMAIN_BLACKLIST, set):
                _MAIL_DOMAIN_BLACKLIST.clear()
                _MAIL_DOMAIN_BLACKLIST.update(self.search([]).mapped('name'))
        except ImportError:
            pass

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_blacklist_rebuild()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._update_blacklist_rebuild()
        return res

    def unlink(self):
        domains_to_remove = self.mapped('name')
        res = super().unlink()
        self._update_blacklist_rebuild()
        return res
