# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _do_change_users_password_to_default(self):
        # change password for every user
        user_login_to_exclude = ['admin@admin.es', 'somadmin@somenergia.coop']
        user_ids = self.env['res.users'].search([
            ('login', 'not in', user_login_to_exclude),
        ])
        default_password = (
            self.env["ir.config_parameter"].sudo().get_param("som_default_password")
        )
        for user_id in user_ids:
            user_id._change_password(default_password)

    def document_view(self):
        self.ensure_one()
        return {
            "name": _("Documents"),
            "domain": [("employee_ref", "=", self.employee_id.id)],
            "res_model": "hr.employee.document",
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "view_type": "form",
            "limit": 80,
            "context": {"default_employee_ref": self.employee_id.id},
        }

    def contract_view(self):
        self.ensure_one()
        return {
            "name": _("Contracts"),
            "domain": [("employee_id", "=", self.employee_id.id)],
            "res_model": "hr.contract",
            "type": "ir.actions.act_window",
            "view_mode": "tree,form",
            "view_type": "form",
            "limit": 80,
            "context": {"default_employee_id": self.employee_id.id},
        }
