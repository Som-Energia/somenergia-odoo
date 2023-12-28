# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    som_comments = fields.Text(
        string="Comments"
    )
