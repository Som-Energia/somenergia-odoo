# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from odoo.addons.iap.tools.iap_tools import _MAIL_DOMAIN_BLACKLIST

# Guardem la llista original d'Odoo un sol cop quan s'inicialitza el mòdul
_ORIGINAL_MAIL_DOMAIN_BLACKLIST = (
    _MAIL_DOMAIN_BLACKLIST.copy() if isinstance(_MAIL_DOMAIN_BLACKLIST, set) else set()
)

class SomCrmMailDomainBlacklist(models.Model):
    _name = 'som.crm.mail.domain.blacklist'
    _description = 'Mail Domain Blacklist'

    name = fields.Char(string='Domain', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company
    )

    @api.model
    @tools.ormcache()
    def get_all_blacklisted_domains(self):
        """
        Retorna la unió dels dominis originals bloquejats per Odoo
        i els dominis personalitzats introduïts pels usuaris a la BBDD.
        Utilitza ormcache per no sobrecarregar la base de dades a cada consulta.
        """
        custom_domains = set(self.search([]).mapped('name'))
        return _ORIGINAL_MAIL_DOMAIN_BLACKLIST.union(custom_domains)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Netejem la memòria cau a TOTS els workers quan es crea un domini
        self.clear_caches()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals:
            # Netejem la memòria cau a TOTS els workers si es modifica el nom
            self.clear_caches()
        return res

    def unlink(self):
        res = super().unlink()
        # Netejem la memòria cau a TOTS els workers quan s'esborra un domini
        self.clear_caches()
        return res