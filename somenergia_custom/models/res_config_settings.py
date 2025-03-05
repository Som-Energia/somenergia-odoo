# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    som_restrictive_stress_days = fields.Boolean(
        related='company_id.som_restrictive_stress_days',
        readonly=False,
    )

    som_restrictive_overtime = fields.Boolean(
        related='company_id.som_restrictive_overtime',
        readonly=False,
    )

    som_amend_attendance_restrictive = fields.Boolean(
        related='company_id.som_amend_attendance_restrictive',
        readonly=False,
    )

    som_amend_attendance_days_to = fields.Integer(
        related='company_id.som_amend_attendance_days_to',
        readonly=False,
    )

    som_attendance_limit_checkin = fields.Float(
        related='company_id.som_attendance_limit_checkin',
        readonly=False,
    )

    som_attendance_limit_checkout = fields.Float(
        related='company_id.som_attendance_limit_checkout',
        readonly=False,
    )
