# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class SomCalendarWeek(models.Model):
    _name = "som.calendar.week"
    _description = "Som Calendar Week"

    name = fields.Char(string="Name")
    som_cw_code = fields.Char(string="Code")
    som_cw_date = fields.Datetime(string="Date")
    som_cw_date_end = fields.Datetime(string="Date End")
    som_cw_week_number = fields.Integer(string="Week number")
    som_cw_week_year = fields.Integer(string="Week year")
    som_cw_year = fields.Integer(string="Year")
