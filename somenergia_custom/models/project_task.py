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

    @api.model_create_multi
    def create(self, vals_list):
        task_ids = super().create(vals_list)
        flag_avoid_default_followers = (
            self.env["ir.config_parameter"].sudo().get_param("som_avoid_default_task_followers")
        )
        if flag_avoid_default_followers:
            for task_id in task_ids:
                partner_to_remove_ids = (task_id.message_partner_ids.user_ids - task_id.user_ids).partner_id
                if partner_to_remove_ids:
                    task_id.sudo().message_follower_ids.filtered(
                        lambda x: x.partner_id.id in partner_to_remove_ids.ids
                    ).unlink()
        return task_ids

    def button_start_work(self):
        internal_project_ids = self.env['project.project'].get_internal_projects()
        timesheets_to_avoid_timer_ids = self.env['account.analytic.line'].search([
            '|',
            ('som_is_cumulative', '=', True),
            ('project_id', 'in', internal_project_ids.ids),
        ])
        result = super().button_start_work()
        result["context"].update({"resuming_lines": timesheets_to_avoid_timer_ids.ids})
        return result
