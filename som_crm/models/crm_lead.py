# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api, _
from erppeek import Client
from odoo.tools import config
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def _default_medium(self):
        medium_id = self.env.ref('utm.utm_medium_direct', raise_if_not_found=False) or False
        return medium_id

    @api.depends('phonecall_ids', 'phonecall_ids.date')
    def _compute_last_call_date(self):
        for record in self:
            if record.phonecall_ids:
                last_call = record.phonecall_ids.sorted(key=lambda x: x.date, reverse=True)
                if last_call:
                    record.som_last_call_date = last_call[0].date
                else:
                    record.som_last_call_date = False
            else:
                record.som_last_call_date = False

    som_cups = fields.Char(
        string='CUPS',
        required=False,
    )

    som_preferred_contact_time_ids = fields.Many2many(
        'contact.time.slot',
        'lead_contact_time_rel',
        'lead_id',
        'time_slot_id',
        string='Preferred contact time',
    )

    som_self_consumption = fields.Selection(
        selection=[
            ("yes", _("Yes")),
            ("no", _("No")),
        ],
        string="Self consumption",
        required=False,
    )

    som_pricelist = fields.Selection(
        selection=[
            ("indexed", _("Indexed")),
            ("periods", _("Periods")),
        ],
        string="Pricelist",
        required=False,
    )

    som_cups_number = fields.Integer(
        string="Number of CUPS",
        default=1,
        required=False,
    )

    medium_id = fields.Many2one(
        'utm.medium',
        required=True,  # Make it required
        ondelete='restrict',
        default=lambda self: self._default_medium(),
    )

    som_erp_lead_id = fields.Integer(
        string='ERP Lead ID',
        required=False,
        help="ID of the lead in the ERP system",
    )

    som_last_call_date = fields.Datetime(
        string='Last Call Date',
        required=False,
        compute='_compute_last_call_date',
        help="Date of the last phone call made to this lead",
    )

    @api.model
    def create(self, vals):
        if not vals.get('medium_id'):
            raise ValidationError("The UTM medium is required for all leads/opportunities.")
        return super().create(vals)

    def write(self, vals):
        if 'medium_id' in vals and not vals['medium_id']:
            raise ValidationError("The UTM medium is required for all opportunities. Can't be deleted.")
        return super().write(vals)

    @api.constrains('medium_id')
    def _check_medium_id(self):
        for record in self:
            if not record.medium_id:
                raise ValidationError("The UTM medium is required for all opportunities.")


    def assign_to_me(self):
        self.write({"user_id": self.env.user.id})

    @api.model
    def get_won_stage(self):
        stage_domain = [
            ('is_won', '=', True),
        ]
        crm_stage_id = self.env['crm.stage'].search(stage_domain, limit=1)
        return crm_stage_id

    @api.model
    def get_leads_to_check(self, won_stage_id=None):
        if not won_stage_id:
            won_stage_id = self.get_won_stage()
            if not won_stage_id:
                _logger.warning("No 'won' stage found, cannot continue")
                return  False

        lead_ids = self.env['crm.lead'].with_context(active_test=False).search([
            ("stage_id", "!=", won_stage_id.id),
            ("type", "=", 'opportunity'),
            # ("active", "!=", False), ??????
        ])
        return lead_ids

    def _erp_search_by_cups(self, erp_lead_obj, domain, cups_value):
        erp_field = 'cups'
        cups_truncated = cups_value[:20]
        domain += [(erp_field, '=ilike', f'{cups_truncated}%')]
        return erp_lead_obj.search(domain, limit=1)

    def _erp_search_by_vat(self, erp_lead_obj, domain, vat_value):
        erp_field = 'titular_vat'
        normalized_vat = vat_value if vat_value.startswith('ES') else f'ES{vat_value}'
        domain += [(erp_field, '=', normalized_vat)]
        return erp_lead_obj.search(domain, limit=1)

    def _erp_search_by_email(self, erp_lead_obj, domain, email_value):
        erp_field = 'titular_email'
        domain += [(erp_field, '=', email_value)]
        return erp_lead_obj.search(domain, limit=1)

    def _erp_search_by_phone(self, erp_lead_obj, domain, phone_value):
        erp_field = 'titular_phone'
        casted_phone = phone_value
        if len(phone_value) > 9:
            casted_phone = phone_value.replace(' ','')[3:]
        domain += [(erp_field, '=', casted_phone)]
        return erp_lead_obj.search(domain, limit=1)

    def get_contract_in_erp(self, erp_lead_obj):
        self.ensure_one()
        search_strategies = {
            'som_cups': self._erp_search_by_cups,
            'vat': self._erp_search_by_vat,
            'email_from': self._erp_search_by_email,
            'phone': self._erp_search_by_phone,
        }

        for lead_field in ['som_cups', 'vat', 'email_from', 'phone']:
            if lead_field not in search_strategies:
                _logger.warning(f"No search strategy for field {lead_field}")
                continue

            value_to_search = getattr(self, lead_field, None)
            if not value_to_search:
                continue
            domain = [('crm_lead_id', '=', False)]
            erp_lead_id = search_strategies[lead_field](erp_lead_obj, domain, value_to_search)
            if erp_lead_id:
                return erp_lead_id

        return False

    @api.model
    def _erp_sync(self):
        won_stage_id = self.get_won_stage()
        if not won_stage_id:
            _logger.warning("No 'won' stage found, cannot proceed with ERP sync")
            return

        lead_ids = self.get_leads_to_check(won_stage_id)
        if not lead_ids:
            _logger.info(f"No leads to check in ERP")
            return
        _logger.info(f"Leads to check in ERP: {len(lead_ids)}")

        _logger.info(f"Connecting to ERP")
        try:
            erppeek = dict(
                server=f"{config.get('erp_uri')}:{config.get('erp_port')}",
                db=config.get('erp_dbname'),
                user=config.get('erp_user'),
                password=config.get('erp_pwd'),
            )
            c = Client(**erppeek)
        except Exception as e:
            _logger.error(f"Error connecting to ERP: {e}")
            return

        erp_lead_obj = c.model("giscedata.crm.lead")

        found_ids = []
        for lead_id in lead_ids:
            erp_lead_id = lead_id.get_contract_in_erp(erp_lead_obj)
            if erp_lead_id:
                found_ids.append(lead_id.id)
                lead_id.som_erp_lead_id = erp_lead_id


        if not found_ids:
            _logger.info("No leads with contract in ERP found")
            return

        lead_to_update_ids = lead_ids.filtered(lambda x: x.id in found_ids)
        lead_to_update_ids.write({'stage_id': won_stage_id.id})

        _logger.info(f"Leads moved to 'Won' stage: {lead_to_update_ids.ids}")
