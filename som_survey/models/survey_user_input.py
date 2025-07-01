# -- coding: utf-8 --
from odoo import models, fields, api, _


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    som_remote_ip = fields.Char(
        string="Remote IP",
    )
