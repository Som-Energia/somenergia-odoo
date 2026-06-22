# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, exceptions, _


class SomCommonProject(models.AbstractModel):
    _name = 'som.common.project'
    _description = 'Som Common Project'

    def _get_project_type_domain_ids(self, reference_date=False):
        reference_date = reference_date or fields.Date.today()
        tag_area_id = self.env.ref("somenergia_custom.som_project_tag_area")
        tag_transversal_id = self.env.ref("somenergia_custom.som_project_tag_transversal_project")

        area_domain = [("tag_ids", "in", tag_area_id.ids)]
        transversal_domain = [("tag_ids", "in", tag_transversal_id.ids)]
        area_domain += [
            '|', ('date_start', '=', False), ('date_start', '<=', reference_date),
            '|', ('date', '=', False), ('date', '>=', reference_date),
        ]

        project_area_ids = self.env['project.project'].search(area_domain)
        project_transversal_ids = self.env['project.project'].search(transversal_domain)
        return project_area_ids, project_transversal_ids

    def _compute_project_type_domain_ids(self):
        for record in self:
            project_area_ids, project_transversal_ids = record._get_project_type_domain_ids()

            record.som_project_area_domain_ids = project_area_ids
            record.som_additional_project_domain_ids = project_transversal_ids

    som_project_area_domain_ids = fields.Many2many(
        "project.project",
        string="Projects area domain",
        compute="_compute_project_type_domain_ids",
        store=False,
    )

    som_additional_project_domain_ids = fields.Many2many(
        "project.project",
        string="Projects no area domain",
        compute="_compute_project_type_domain_ids",
        store=False,
    )
