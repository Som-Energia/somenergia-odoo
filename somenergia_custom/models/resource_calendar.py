# -*- coding: utf-8 -*-
import random

from odoo import models, fields, _


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    som_max_overtime_per_day = fields.Float(
        striing="Max overtime per day",
        default=1,
        help="Maximum amount of overtime hours per day"
    )
