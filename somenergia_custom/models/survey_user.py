# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    @api.depends('appraisal_id', 'appraisal_id.appraisal_deadline')
    def _compute_deadline(self):
        for record in self.filtered(lambda x: x.appraisal_id and x.appraisal_id.appraisal_deadline):
            record.deadline = record.appraisal_id.appraisal_deadline

    deadline = fields.Datetime(
        compute="_compute_deadline",
        copy=False,
        readonly=False,
        store=True,
    )
