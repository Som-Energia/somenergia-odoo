# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _, _lt

_logger = logging.getLogger(__name__)


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

        name = f'Lead from phonecall {self.som_phone}'
        if not res.get('name', False):
            res.update({'name': name})

        res.update({
            'medium_id': utm_medium_phone_id.id if utm_medium_phone_id else False,
            'contact_name': self.som_caller_name,
            'email_from': self.email_from,
            'phone': self.som_phone,
            'vat': self.som_caller_vat,
            'user_id': user_id.id if user_id else False,
        })
        return res

    @api.model
    def _convert_to_opportunity_by_category(self):
        crm_category_id = self.env.company.som_crm_call_category_id
        pc_ids = self.env['crm.phonecall'].search([
            ('som_category_ids', 'in', [crm_category_id.id]),
            ('opportunity_id', '=', False),
        ])
        _logger.info(f"Phone calls to convert: {len(pc_ids)}")
        # We do it with a for because the function is ensure_one
        for pc_id in pc_ids:
            pc_id.action_button_convert2opportunity()
        _logger.info(f"{len(pc_ids)} Phone calls converted successfully")
