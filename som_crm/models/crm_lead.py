# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api, _
from erppeek import Client
from odoo.tools import config
from odoo.exceptions import ValidationError
from urllib.parse import urlparse, parse_qs

_logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def _default_medium(self):
        medium_id = self.env.ref('utm.utm_medium_direct', raise_if_not_found=False) or False
        return medium_id

    @api.depends('phonecall_ids', 'phonecall_ids.date', 'phonecall_ids.som_phone_call_result_id')
    def _compute_last_call_date(self):
        for record in self:
            if record.phonecall_ids:
                last_call = record.phonecall_ids.filtered(
                    lambda x: not x.som_phone_call_result_id.not_contacted
                ).sorted(key=lambda x: x.date, reverse=True)
                if last_call:
                    record.som_last_call_date = last_call[0].date
                    record.som_last_call_date_only = last_call[0].date.date()
                else:
                    record.som_last_call_date = False
                    record.som_last_call_date_only = False
            else:
                record.som_last_call_date = False
                record.som_last_call_date_only = False

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

    medium_id = fields.Many2one(
        'utm.medium',
        required=False,
        ondelete='restrict',
        # default=lambda self: self._default_medium(),
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
        store=True,
    )

    som_last_call_date_only = fields.Date(
        string='Last Call Date Only',
        required=False,
        compute='_compute_last_call_date',
        help="Date of the last phone call made to this lead",
        store=True,
    )

    som_comparison_result = fields.Selection(
        selection=[
            ("favourable", _("favourable")),
            ("disfavourable", _("disfavourable")),
        ],
        string="Comparison Result",
        required=False,
    )

    som_channel = fields.Many2one(
        'utm.medium',
        string='Channel',
        required=False,
        help="Channel through which the lead was acquired",
        default=lambda self: self._default_medium(),
    )

    som_url_origin = fields.Char('URL Origin', help="URL from which the lead originated")

    def auto_assign_user(self):
        team_id = self.env.ref(
            'sales_team.team_sales_department', raise_if_not_found=False
        ) or False
        team_user_id = team_id.user_id if team_id else False
        if team_user_id:
            for record in self.filtered(lambda x: not x.user_id):
                record.user_id = team_user_id

    def do_opportunity_from_fetchmail(self):
        self.auto_assign_user()
        medium_form_id = self.env.ref(
            'som_crm.som_medium_webform', raise_if_not_found=False
        ) or False
        if medium_form_id:
            for record in self.filtered(lambda x: x.som_channel != medium_form_id):
                record.som_channel = medium_form_id

    @api.model
    def create(self, vals):
        lead_id = super(Lead, self).create(vals)
        if (self.env.context.get('fetchmail_cron_running', False) and
                self.env.context.get('default_fetchmail_server_id', False)):
            lead_id.do_opportunity_from_fetchmail()
        return lead_id

    def assign_to_me(self):
        self.write({"user_id": self.env.user.id})

    def assign_partner(self):
        for record in self.filtered(lambda x: not x.partner_id):
            partner = record._find_matching_partner_custom()
            if partner:
                record.partner_id = partner.id
            else:
                if not (record.contact_name) or not (record.email_from or record.phone):
                    raise ValidationError(
                        _("Cannot create partner without name and email or phone.")
                    )
                record._handle_partner_assignment(create_missing=True)

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
        email_value_upper = email_value.upper()
        domain += ["|",(erp_field, '=', email_value), (erp_field, '=', email_value_upper)]
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
            domain = [('crm_lead_id', '=', 0)]
            erp_lead_id = search_strategies[lead_field](erp_lead_obj, domain, value_to_search)
            if erp_lead_id:
                return erp_lead_id[0]

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
                erp_lead_obj.write(erp_lead_id, {'crm_lead_id': lead_id.id})
                lead_id.som_erp_lead_id = erp_lead_id
                found_ids.append(lead_id.id)

        if not found_ids:
            _logger.info("No leads with contract in ERP found")
            return

        lead_to_update_ids = lead_ids.filtered(lambda x: x.id in found_ids)
        lead_to_update_ids.write({'stage_id': won_stage_id.id})

        _logger.info(f"Leads moved to 'Won' stage: {lead_to_update_ids.ids}")

    def button_open_phonecall(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "crm_phonecall.crm_case_categ_phone_incoming0"
        )
        action['context'] = {
            "default_opportunity_id": self.id,
            "search_default_opportunity_id": self.id,
            "default_partner_id": self.partner_id.id,
            "default_duration": 1.0,
        }
        return action

    def _find_matching_partner_custom(self):
        self.ensure_one()
        partner = self.partner_id

        if not partner and self.email_from:
            partner = self.env['res.partner'].search([('email', '=', self.email_from)], limit=1)

        if not partner and self.phone:
            partner = self.env['res.partner'].search([('phone', '=', self.phone)], limit=1)

        return partner

    @api.model
    def _get_utm_data_from_url(self, url):
        """
        Extrac params from URL.
        Args:
            url (str): URL to parse
            sample:
            https://uneixte.somenergia.coop/ca/landing/captacio-domestic/?mtm_cid=20250924&mtm_campaign=uneixte&mtm_medium=Especial&mtm_content=CA&mtm_source=instagram

        Returns:
            dict: dictionary with UTM and MTM params if found
            {'mtm_source': 'instagram',
             'mtm_medium': 'Especial',
             'mtm_campaign': 'uneixte',
             'mtm_content': 'CA',
             'mtm_cid': '20250924'
             }
        """
        parsed_url = urlparse(url)

        params = parse_qs(parsed_url.query)

        tracking_data = {}

        tracking_params = [
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'mtm_source', 'mtm_medium', 'mtm_campaign', 'mtm_keyword', 'mtm_content',
            'mtm_cid', 'mtm_group'
        ]

        for param in tracking_params:
            if param in params:
                tracking_data[param] = params[param][0]

        return tracking_data

    @api.model
    def _find_or_create_utm_record(self, model_name, name):
        record_id = self.env[model_name].sudo().search([('name', '=', name)], limit=1)
        if not record_id:
            record_id = self.env[model_name].sudo().create({'name': name})
        return record_id

    def process_utm_data(self):
        """
        Processes UTM parameters from a URL, searching or creating the corresponding
        records for campaign, medium, and source.
        """
        # Define the field mappings (Result key: (Model Name, Priority Key 1, Priority Key 2))
        utm_mappings = {
            'campaign_id': ('utm.campaign', 'mtm_campaign', 'utm_campaign'),
            'medium_id': ('utm.medium', 'mtm_medium', 'utm_medium'),
            'source_id': ('utm.source', 'mtm_source', 'utm_source'),
        }

        for record in self.filtered(lambda x: x.som_url_origin):
            dict_update = {}
            # Get the UTM data
            utm_data = self._get_utm_data_from_url(record.som_url_origin)

            # Process each UTM type
            for res_key, (model_name, key1, key2) in utm_mappings.items():
                # Get the UTM name, prioritizing the 'mtm' version
                name = utm_data.get(key1) or utm_data.get(key2)
                if name:
                    # Call the helper function to find or create the record
                    record_id = self._find_or_create_utm_record(model_name, name)
                    dict_update[res_key] = record_id.id
                else:
                    dict_update[res_key] = False

            record.write(dict_update)
