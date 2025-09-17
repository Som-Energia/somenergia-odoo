
from odoo import models, fields, api


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    phone_call_result = fields.Selection([
        ('answered', 'Answered'),
        ('no_answer', 'No Answer'),
        ('busy', 'Busy'),
        ('wrong_number', 'Wrong Number'),
        ('callback_requested', 'Callback Requested'),
        ('not_interested', 'Not Interested'),
        ('interested', 'Interested'),
        ('follow_up_needed', 'Follow-up Needed'),
    ], string='Phone Call Result', help="Result of the phone call activity")

