# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt


class Task(models.Model):
    _name = "project.task"
    _inherit = ["project.task", "som.common.project"]

    som_department_ids = fields.Many2many(
        'hr.department', 'som_task_department_rel',
        'task_id', 'department_id',
        string='Departments',
    )

    som_project_id = fields.Many2one(
        comodel_name="project.project",
        string="Area project"
    )

    som_additional_project_id = fields.Many2one(
        comodel_name="project.project",
        string="Transversal project"
    )

    def name_get(self):
        res = []
        for task_id in self:
            name = "[#%s] %s" % (str(task_id.id), task_id.name)
            res += [(task_id.id, name)]
        return res
