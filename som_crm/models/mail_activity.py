from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    phone_call_result_id = fields.Many2one(
        'phone.call.result',
        string='Phone Call Result',
        help="Result of the phone call activity"
    )

    phone_call_duration = fields.Float(
        string='Phone Call Duration',
        help="Duration of the phone call in minutes and seconds",
    )

    def _action_done(self, feedback=False, attachment_ids=None):
        """ Override to include phone call result in the feedback when available. """
        if self.activity_category == 'phonecall' and not self.phone_call_result_id:
            raise ValidationError("The phone call result is required for all done calls.")
        if self.activity_category == 'phonecall' and self.phone_call_result_id:
            if feedback:
                feedback = f"{feedback}\n\n<strong>Phone Call Result:</strong> {self.phone_call_result_id.name}"
            else:
                feedback = f"<strong>Phone Call Result:</strong>{self.phone_call_result_id.name}"
            if self.res_model == 'crm.lead':
                lead = self.env['crm.lead'].browse(self.res_id)
            self.env['crm.phonecall'].create({
                'name': self.summary or 'Phone Call',
                'som_phone_call_result_id': self.phone_call_result_id.id,
                'direction': 'out',
                'user_id': self.user_id.id,
                'duration': self.phone_call_duration,
                'opportunity_id': self.res_id if self.res_model == 'crm.lead' else False,
                'partner_id': lead.partner_id.id if self.res_model == 'crm.lead' else False,
                'som_phone': lead.phone if self.res_model == 'crm.lead' else False,
                'description': self.note,
            })
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)