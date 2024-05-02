# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt


class CrmPhonecall(models.Model):
    _name = 'crm.phonecall'
    _inherit = ['crm.phonecall', 'som.callinfo.endpoint']

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
