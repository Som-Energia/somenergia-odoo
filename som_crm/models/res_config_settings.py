# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    som_crm_call_category_id = fields.Many2one(
        related='company_id.som_crm_call_category_id',
        readonly=False,
    )

    som_ff_call_to_opportunity = fields.Boolean(
        related='company_id.som_ff_call_to_opportunity',
        readonly=False,
    )

    som_ff_send_lead_confirmation_email = fields.Boolean(
        related='company_id.som_ff_send_lead_confirmation_email',
        readonly=False,
    )

    som_ff_send_lead_confirmation_email_from = fields.Char(
        related='company_id.som_ff_send_lead_confirmation_email_from',
        readonly=False,
    )

    som_ff_auto_upcomming_activity = fields.Boolean(
        related='company_id.som_ff_auto_upcomming_activity',
        readonly=False,
    )
