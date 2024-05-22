# -*- coding:utf-8 -*-
from odoo import api, models, fields, _
from odoo.tests import common, Form


class HrContract(models.Model):
    _inherit = 'hr.contract'

    kanban_state = fields.Selection(default='done')

    @api.model
    def update_state(self):
        res = super().update_state()
        return res

    def create_approval_from_contract(self):
        for record in self:
            description = _("%s passa a %s" % (
                record.employee_id.name,
                record.pnt_rank_id.name if record.pnt_rank_id else "",
            ))
            # TODO: create conf approval or XML_ID for this type
            approval_type_id = self.env['multi.approval.type'].browse(6)
            # approval_type_id = self.env.ref(
            #     "somenergia_custom.som_approval_type_payroll_change", raise_if_not_found=False
            # ) or False
            dict_create = {
                'user_id': record.hr_responsible_id.id,
                'name': description,
                'description': description,
                'pnt_employee_id': record.employee_id.id,
                'date': record.date_start,
                'type_id': approval_type_id.id,
                'pic_id': record.hr_responsible_id.id,
            }
            self.env['multi.approval'].create(dict_create)
