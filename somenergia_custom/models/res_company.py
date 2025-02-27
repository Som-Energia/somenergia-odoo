# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    som_restrictive_stress_days = fields.Boolean(
        string="Restrictive stress days",
        default=True,
    )

    som_restrictive_overtime = fields.Boolean(
        string="Restrictive overtime",
        default=False,
    )

    som_amend_attendance_restrictive = fields.Boolean(
        string="Restrictive amend attendance",
        default=False,
    )

    som_amend_attendance_days_to = fields.Integer(
        string="Days to amend attendance",
        default=1,
    )
