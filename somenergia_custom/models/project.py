# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt
from odoo.modules.module import get_module_resource


class Project(models.Model):
    _inherit = 'project.project'

    @api.depends('tag_ids')
    def _compute_som_is_internal_project(self):
        tag_area_id = (
                self.env.ref("somenergia_custom.som_project_tag_area", raise_if_not_found=False) or False
        )
        tag_transversal_id = (
                self.env.ref("somenergia_custom.som_project_tag_transversal_project", raise_if_not_found=False) or False
        )
        tag_worked_id = self.env.ref("somenergia_custom.som_project_tag_worked", raise_if_not_found=False) or False
        list_tags = [
            tag_area_id.id if tag_area_id else 0,
            tag_transversal_id.id if tag_transversal_id else 0,
            tag_worked_id.id if tag_worked_id else 0,
        ]
        for project_id in self:
            list_aux = [id for id in project_id.tag_ids.ids if id in list_tags]
            project_id.som_is_internal_project = (len(list_aux) > 0)

    som_is_internal_project = fields.Boolean(
        string='Som internal project',
        compute='_compute_som_is_internal_project',
        store=True,
    )

    def _load_default_tasks(self):
        user_somadmin_id = self.env['res.users'].search([
            ('login', '=', 'somadmin@somenergia.coop'),
        ])

        project_ids = self.env['project.project'].search([
            ('task_ids', '=', False)
        ])

        for project_id in project_ids:
            # create default task
            values = dict(name=project_id.name, project_id=project_id.id)
            task_id = self.env['project.task'].with_user(
                user_somadmin_id or self.env.user
            ).create(values)

    def _load_table_calendar_weeks(self):
        calendar_week_ids = self.env['som.calendar.week'].search([])
        if not calendar_week_ids:
            query_name = "query_load_calendar_weeks.sql"
            query_file = get_module_resource(
                "somenergia_custom", "query", query_name
            )
            query = open(query_file).read()
            cr = self.env.cr
            cr.execute(query)

    @api.model
    def get_internal_projects(self):
        internal_tag_ids = self.env['project.tags'].search([
            ('som_for_internal_project', '=', True),
        ])
        internal_project_ids = self.env['project.project'].search([
            ('tag_ids', 'in', internal_tag_ids.ids),
        ])
        return internal_project_ids

    @api.model
    def _do_initialize_projects(self):
        self._load_default_tasks()
        self._load_table_calendar_weeks()


class ProjectTags(models.Model):
    _inherit = "project.tags"

    som_for_internal_project = fields.Boolean(
        string='Som for internal project',
        store=True,
    )
