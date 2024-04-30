# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt


class CrmPhonecall(models.Model):
    _name = 'crm.phonecall'
    _inherit = ['crm.phonecall', 'som.callinfo.endpoint']

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
        # self.check_category_model()
        self.check_call_models()
        self.get_phonecall_categories()
