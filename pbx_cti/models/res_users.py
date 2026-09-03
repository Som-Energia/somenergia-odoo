# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    pbx_extension = fields.Char(
        string="PBX Extension",
        help="Extension number assigned to this user in the PBX (e.g. 201).",
    )
