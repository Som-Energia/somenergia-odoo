# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
import logging
import datetime
from datetime import timedelta
_logger = logging.getLogger(__name__)


class HrAppraisalGenerateWizard(models.TransientModel):
    _name = 'hr.appraisal.generate.wizard'

    som_feedback_type = fields.Selection(
        selection=[
            ("annual_360", "Feedback annual 360"),
        ],
        string="Type",
        required=True,
    )

    som_year = fields.Integer(
        string="Year",
        default=fields.Datetime.today().year,
    )

    @api.model
    def default_get(self, fields):
        record_ids = self._context.get('active_ids')
        result = super(HrAppraisalGenerateWizard, self).default_get(fields)
        return result

    def do_process(self):
        from_date = datetime.datetime(self.som_year, 1, 1)
        to_date = datetime.datetime(self.som_year, 12, 31)
        employee_with_feedback_ids = self.env['hr.appraisal'].search([
            ('appraisal_date', '>=', fields.Date.to_string(from_date)),
            ('appraisal_date', '<=', fields.Date.to_string(to_date)),
        ]).mapped('emp_id')

        employee_ids = self.env['hr.employee'].search([
            ('som_recruitment_date', '!=', False),
            ('id', 'not in', employee_with_feedback_ids.ids),
        ])

        for employee_id in employee_ids:
            appraisal_date = datetime.datetime(
                self.som_year, employee_id.som_recruitment_date.month, employee_id.som_recruitment_date.day
            )
            dict_create = {
                'emp_id': employee_id.id,
                'appraisal_date': fields.Date.to_string(appraisal_date),
                'appraisal_deadline': fields.Date.to_string(appraisal_date + timedelta(days=30)),
                'som_type': self.som_feedback_type,
            }
            self.env['hr.appraisal'].create(dict_create)
