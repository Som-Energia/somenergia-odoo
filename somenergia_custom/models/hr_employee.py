# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    is_present = fields.Boolean(
        string='Present today',
        compute='_compute_is_present',
        store=False,
        search='_search_present_employee'
    )

    def _compute_is_present(self):
        for record in self:
            record.is_present = not record.is_absent

    def _search_present_employee(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        employee_ids = self.env['hr.employee'].search([('is_absent', '=', False)])
        operator = ['in', 'not in'][(operator == '=') != value]
        return [('id', operator, employee_ids.ids)]
