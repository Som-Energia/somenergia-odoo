# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Department(models.Model):
    _name = 'hr.department'
    _inherit = ['hr.department', 'som.common.project']

    som_project_area_id = fields.Many2one(
        'project.project',
        string='Default Project Area',
        help='Project area associated with this department, used for timesheet entries',
    )
