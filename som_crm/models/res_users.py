# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    som_call_center_user = fields.Char(
        string='Call center user',
        required=False,
    )

    @api.constrains('som_call_center_user')
    def _check_call_center_user(self):
        for record in self:
            count = self.search_count(
                [
                    ("id", "!=", record.id),
                    ("som_call_center_user", "!=", ""),
                    ("som_call_center_user", "=", record.som_call_center_user),
                ]
            )
            if count:
                raise ValidationError(_("The field 'Call center user' must be unique."))
