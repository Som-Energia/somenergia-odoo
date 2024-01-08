# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class HRAttendanceOvertime(models.Model):
    _inherit = "hr.attendance.overtime"

    def action_view_attendances(self):
        # action_id = self.env.ref('hr_attendance.hr_attendance_action')
        tree_view_id = self.env.ref('hr_attendance.view_attendance_tree')
        date_to = fields.Date.add(self.date, days=1)
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', self.date),
            ('check_out', '<', date_to)
        ]
        action_open_attendances = {
            'name': _('Day attendances %s' % self.date.strftime("%d/%m/%Y")),
            'view_type': 'tree',
            'res_model': 'hr.attendance',
            'domain': domain,
            'view_id': tree_view_id.id,
            'views': [
                (tree_view_id.id, 'tree'),
            ],
            'type': 'ir.actions.act_window',
        }

        return action_open_attendances
