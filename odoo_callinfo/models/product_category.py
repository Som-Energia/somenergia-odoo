# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt
from datetime import datetime, timezone, timedelta
from random import randint
import json

RGB_COLORS = {
    1: {'rgb': "#F06050", 'name': 'Red'},
    2: {'rgb': "#F4A460", 'name': 'Orange'},
    3: {'rgb': "#F7CD1F", 'name': 'Yellow'},
    4: {'rgb': "#6CC1ED", 'name': 'Light blue'},
    5: {'rgb': "#814968", 'name': 'Dark purple'},
    6: {'rgb': "#EB7E7F", 'name': 'Salmon pink'},
    7: {'rgb': "#2C8397", 'name': 'Medium blue'},
    8: {'rgb': "#475577", 'name': 'Dark blue'},
    9: {'rgb': "#D6145F", 'name': 'Fushia'},
    10: {'rgb': "#30C381", 'name': 'Green'},
    11: {'rgb': "#9365B8", 'name': 'Purple'},
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
            ancestors = self.parent_id._get_ancestors()
        else:
            ancestors = []
        ancestors.append(self.id)
        return ancestors

    @api.depends('som_code', 'parent_id.som_code', 'parent_id.som_full_code')
    def _compute_full_code(self):
        for record in self:
            parents_list = record._get_ancestors()
            parent_ids = self.env['product.category'].browse(parents_list)
            record.som_full_code = '-'.join([c_id.som_code for c_id in parent_ids if c_id.som_code])

    @api.depends('parent_id')
    def _compute_level(self):
        for record in self:
            ancestors_list = record._get_ancestors()
            count_ancestors = len(ancestors_list) - 1
            # set ancestors
            field_name = 'som_ancestor_level'
            for i in range(0, 3):
                field_name_aux = field_name + str(i)
                if i < count_ancestors:
                    record[field_name_aux] = ancestors_list[i]
                else:
                    record[field_name_aux] = False
            # set level
            record.som_level = count_ancestors

    @api.depends('som_ancestor_level1', 'som_ancestor_level1.som_color', 'som_color')
    def _compute_family_color(self):
        for record in self:
            record.som_family_color = (
                record.som_ancestor_level1.som_color
                if record.som_ancestor_level1
                else record.som_color
            )

    som_code = fields.Char(string="Code")

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

    som_ancestor_level0 = fields.Many2one(
        comodel_name= 'product.category',
        string='Ancestor Level 0',
        index=True,
        compute='_compute_level',
        store=True,
    )
    som_ancestor_level1 = fields.Many2one(
        comodel_name='product.category',
        string='Ancestor Level 1',
        index=True,
        compute='_compute_level',
        store=True,
    )
    som_ancestor_level2 = fields.Many2one(
        comodel_name='product.category',
        string='Ancestor Level 2',
        index=True,
        compute='_compute_level',
        store=True,
    )
    som_ancestor_level3 = fields.Many2one(
        comodel_name='product.category',
        string='Ancestor Level 3',
        index=True,
        compute='_compute_level',
        store=True,
    )

    som_color = fields.Integer('Color', default=_get_default_color)

    som_family_color = fields.Integer(
        string='Family color',
        compute='_compute_family_color',
        store=True,
    )

    som_keyword_ids = fields.Many2many(
        comodel_name="crm.tag",
        relation="som_category_tag_rel",
        column1="category_id",
        column2="tag_id",
        string="Keywords",
        store=True,
    )

