# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, _lt
from odoo.modules.module import get_module_resource


class Project(models.Model):
    _inherit = 'project.project'

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
            # result = []
            cr.execute(query)
            # result = cr.fetchall()

    @api.model
    def _do_initialize_projects(self):
        self._load_default_tasks()
        self._load_table_calendar_weeks()
        pass
