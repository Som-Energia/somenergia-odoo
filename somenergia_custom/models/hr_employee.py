# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    som_current_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
    )


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _compute_is_present(self):
        for record in self:
            record.is_present = not record.is_absent

    @api.depends('calendar_ids', 'calendar_ids.date_start', 'calendar_ids.date_end')
    def _compute_current_calendar(self):
        for record in self:
            calendar_id = record.calendar_ids.filtered(
                lambda x: (x.date_start and x.date_start <= fields.Date.today() and not x.date_end) or
                          (not x.date_start and not x.date_end)
            )
            record.som_current_calendar_id = calendar_id[0].calendar_id.id if calendar_id else False

    def _search_present_employee(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        employee_ids = self.env['hr.employee'].search([('is_absent', '=', False)])
        operator = ['in', 'not in'][(operator == '=') != value]
        return [('id', operator, employee_ids.ids)]

    is_present = fields.Boolean(
        string='Present today',
        compute='_compute_is_present',
        store=False,
        search='_search_present_employee'
    )

    som_current_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Current calendar",
        compute='_compute_current_calendar',
        store=True,
        compute_sudo=True,
    )


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    department_ids = fields.Many2many(
        readonly=True,
    )

    som_current_calendar_id = fields.Many2one(
        readonly=True,
    )
