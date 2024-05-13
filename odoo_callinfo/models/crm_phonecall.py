# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt


class CrmPhonecall(models.Model):
    _name = 'crm.phonecall'
    _inherit = ['crm.phonecall', 'som.callinfo.endpoint']

    direction = fields.Selection(default="in")

    som_operator = fields.Char(
        string="Operator",
    )

    som_pbx_call_id = fields.Char(
        string="Pbx call id",
    )

    som_phone = fields.Char(
        string="Phone number",
    )

    som_caller_erp_id = fields.Integer(
        string="Caller ERP Id",
    )
    som_caller_name = fields.Char(
        string="Caller name",
    )
    som_caller_vat = fields.Char(
        string="Caller VAT",
    )

    som_contract_erp_id = fields.Integer(
        string="Contract ERP Id",
    )
    som_contract_name = fields.Char(
        string="Contract name",
    )
    som_contract_address = fields.Char(
        string="Contract address",
    )

    som_category_ids = fields.Many2many(
        comodel_name="product.category",
        relation="som_call_category_rel",
        column1="call_id",
        column2="category_id",
        string="Categories",
        store=True,
    )

    def do_action(self):
        # self.check_pydantic_model()
        # self.check_category_models()
        # self.check_call_models()
        res = self.get_phonecall_categories()
        pass

    @api.model
    def _get_calls_by_operator(self, operator, limit=None, date_from=None, date_to=None):
        domain = [
            ('som_operator', '=', operator)
        ]
        if date_from:
            domain.append(('date', '>=', fields.Date.to_string(date_from)))
        if date_to:
            domain.append(('date', '<=', fields.Date.to_string(date_to)))

        call_ids = self.search(domain, order='date desc', limit=limit)
        return call_ids
