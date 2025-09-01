# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt


class CrmPhonecall(models.Model):
    _name = 'crm.phonecall'
    _inherit = ['crm.phonecall']

    def _prepare_opportunity_vals(self):
        res = super()._prepare_opportunity_vals()

        utm_medium_phone_id = self.env.ref('utm.utm_medium_phone', raise_if_not_found=False) or False
        res.update({
            'medium_id': utm_medium_phone_id.id if utm_medium_phone_id else False,
            'contact_name': self.som_caller_name,
            'email_from': self.email_from,
            'phone': self.som_phone,
            'vat': self.som_caller_vat,
        })
        return res
