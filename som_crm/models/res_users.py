# -*- coding: utf-8 -*-
from odoo import api, models, fields, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    som_call_center_user = fields.Char(
        string='Call center user',
        required=False,
    )
