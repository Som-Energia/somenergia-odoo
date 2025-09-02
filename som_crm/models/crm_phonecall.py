# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt


class CrmPhonecall(models.Model):
    _name = 'crm.phonecall'
    _inherit = ['crm.phonecall']


    def _get_user_crm(self):
        user_id = self.env['res.users'].search([
            ('som_call_center_user', '=', self.som_operator),
        ], limit = 1)
        return user_id or False

    def _prepare_opportunity_vals(self):
        res = super()._prepare_opportunity_vals()

        utm_medium_phone_id = self.env.ref('utm.utm_medium_phone', raise_if_not_found=False) or False

        user_id = self._get_user_crm()

        res.update({
            'medium_id': utm_medium_phone_id.id if utm_medium_phone_id else False,
            'contact_name': self.som_caller_name,
            'email_from': self.email_from,
            'phone': self.som_phone,
            'vat': self.som_caller_vat,
            'user_id': user_id.id if user_id else False,
        })
        return res
