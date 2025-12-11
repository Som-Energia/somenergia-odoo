# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    som_call_center_user = fields.Char(
        string='Call center user',
        required=False,
    )

    som_max_leads_capacity = fields.Integer(
        string='Max leads capacity',
        required=False,
        default=50,
        help='Maximum number of leads that can be assigned to this user. 0 means unlimited.',
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

    def _get_assigned_opportunities_count(self):
        """ Returns the number of opportunities assigned to the user. """
        self.ensure_one()
        return self.env['crm.lead'].search_count([
            ('user_id', '=', self.id),
            ('type', '=', 'opportunity'),
        ])

    def _get_available_leads_capacity(self):
        """ Returns the number of available leads capacity for the user. """
        self.ensure_one()
        if self.som_max_leads_capacity == 0:
            return float('inf') # Unlimited capacity
        assigned_opportunities_count = self._get_assigned_opportunities_count()
        if assigned_opportunities_count >= self.som_max_leads_capacity:
            return 0
        return self.som_max_leads_capacity - assigned_opportunities_count
