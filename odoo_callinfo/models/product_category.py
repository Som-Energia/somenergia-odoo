# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt
from datetime import datetime, timezone, timedelta
from random import randint
import json

RGB_COLORS = {
    1: "#F06050",
    2: "#F4A460",
    3: "#F7CD1F",
    4: "#6CC1ED",
    5: "#814968",
    6: "#EB7E7F",
    7: "#2C8397",
    8: "#475577",
    9: "#D6145F",
    10: "#30C381",
    11: "#9365B8",
}


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.model
    def _get_color_rgb(self, color_index):
        return RGB_COLORS[color_index]

    def _get_default_color(self):
        return randint(1, 11)

    def _get_ancestors(self):
        self.ensure_one()
        if self.parent_id:
            parents = self.parent_id._get_ancestors()
        else:
            parents = []
        parents.append(self.id)
        return parents

    @api.depends('som_code', 'parent_id.som_code', 'parent_id.som_full_code')
    def _compute_full_code(self):
        for record in self:
            parents_list = record._get_ancestors()
            parent_ids = self.env['product.category'].browse(parents_list)
            record.som_full_code = '-'.join([c_id.som_code for c_id in parent_ids if c_id.som_code])

    @api.depends('parent_id')
    def _compute_level(self):
        for record in self:
            parents_list = record._get_ancestors()
            record.som_level = len(parents_list)

    som_full_code = fields.Char(
        string="Full code",
        compute='_compute_full_code',
        recursive=True,
        store=True,
    )

    som_level = fields.Integer(
        string="Level",
        compute='_compute_level',
        store=True,
    )

    som_code = fields.Char(string="Code")

    som_color = fields.Integer('Color', default=_get_default_color)

    som_keyword_ids = fields.Many2many(
        comodel_name="crm.tag",
        relation="som_category_tag_rel",
        column1="category_id",
        column2="tag_id",
        string="Keywords",
        store=True,
    )

