# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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

    som_crm_daily_won_leads_target = fields.Integer(
        string="Objectiu Diari de Leads Guanyats",
        config_parameter='som_crm_daily_won_leads_target',
        default=0
    )

    som_crm_erp_contract_match_days = fields.Integer(
        string="Marge de dies per vincular contractacions ERP",
        config_parameter='som_crm_erp_contract_match_days',
        default=10,
    )

    @api.constrains('som_crm_erp_contract_match_days')
    def _check_erp_contract_match_days(self):
        for settings in self:
            if settings.som_crm_erp_contract_match_days < 0:
                raise ValidationError(
                    _("The ERP contract matching day margin cannot be negative.")
                )

    som_crm_lead_welcome_template_id = fields.Many2one(
        related='company_id.som_crm_lead_welcome_template_id',
        readonly=False,
    )

    som_crm_lead_welcome_template_es_id = fields.Many2one(
        related='company_id.som_crm_lead_welcome_template_es_id',
        readonly=False,
    )

    som_crm_lead_welcome_stage_id = fields.Many2one(
        related='company_id.som_crm_lead_welcome_stage_id',
        readonly=False,
    )
