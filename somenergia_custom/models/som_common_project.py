# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields, exceptions, _


class SomCommonProject(models.AbstractModel):
    _name = 'som.common.project'
    _description = 'Som Common Project'

    def _compute_project_type_domain_ids(self):
        tag_area_id = self.env.ref("somenergia_custom.som_project_tag_area")
        tag_transversal_id = self.env.ref("somenergia_custom.som_project_tag_transversal_project")
        for record in self:
            domain = [("tag_ids", "in", tag_area_id.ids)]
            domain_no_area = [("tag_ids", "in", tag_transversal_id.ids)]

            project_area_ids = self.env['project.project'].search(domain)
            project_transversal_ids = self.env['project.project'].search(domain_no_area)

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
