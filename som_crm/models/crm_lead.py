# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api, _
from erppeek import Client
from odoo.tools import config

_logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = 'crm.lead'

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

    def _erp_search_by_cups(self, polissa_obj, cups_value):
        erp_field = 'cups.name'
        cups_truncated = cups_value[:20]
        domain = [(erp_field, '=ilike', f'{cups_truncated}%')]
        return polissa_obj.search(domain, limit=1)

    def _erp_search_by_vat(self, polissa_obj, vat_value):
        erp_field = 'titular_nif'
        normalized_vat = vat_value if vat_value.startswith('ES') else f'ES{vat_value}'
        domain = [(erp_field, '=', normalized_vat)]
        return polissa_obj.search(domain, limit=1)

    def get_contract_in_erp(self, polissa_obj):
        self.ensure_one()
        search_strategies = {
            'som_cups': self._erp_search_by_cups,
            'vat': self._erp_search_by_vat,
        }

        for lead_field in ['som_cups', 'vat']:
            if lead_field not in search_strategies:
                _logger.warning(f"No search strategy for field {lead_field}")
                continue

            value_to_search = getattr(self, lead_field, None)
            if not value_to_search:
                continue

            polissa_id = search_strategies[lead_field](polissa_obj, value_to_search)
            if polissa_id:
                return polissa_id

        return False

    # def is_contracted_in_erp_mine(self, polissa_obj):
    #     self.ensure_one()
    #     polissa_id = False

    #     for lead_field, erp_field in MAPPED_FIELDS_LEAD_ERP.items():
    #         polissa_id = False
    #         value_to_search = getattr(self, lead_field)
    #         if not value_to_search:
    #             continue
    #         domain = []

    #         if lead_field == 'som_cups':
    #             value_to_search = value_to_search[:20]
    #             domain = [(erp_field, '=ilike', '{}%'.format(value_to_search))]
    #             polissa_id = polissa_obj.search(domain)
    #             if polissa_id:
    #                 return polissa_id

    #         if lead_field == 'vat':
    #             value_to_search = 'ES{}'.format(value_to_search) if (
    #                 not value_to_search.startswith('ES')
    #             ) else value_to_search
    #             domain = [(erp_field, '=', value_to_search)]
    #             polissa_id = polissa_obj.search(domain)
    #             if polissa_id:
    #                 return polissa_id

    #     return polissa_id or False

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

        polissa_obj = c.model("giscedata.polissa")

        found_ids = []
        for lead in lead_ids:
            pol_id = lead.get_contract_in_erp(polissa_obj)
            if pol_id:
                found_ids.append(lead.id)
                # TODO: new field to store ERP contract ID?

        if not found_ids:
            _logger.info("No leads with contract in ERP found")
            return

        lead_to_update_ids = lead_ids.filtered(lambda x: x.id in found_ids)
        lead_to_update_ids.write({'stage_id': won_stage_id.id})

        _logger.info(f"Leads moved to 'Won' stage: {lead_to_update_ids.ids}")

    @api.model
    def _erp_proof_of_concept_connect(self):
        lead_ids = self.get_leads_to_update()
        if not lead_ids:
            return
        _logger.info(f"Leads to update: {lead_ids}")

        _logger.info(f"Connecting to ERP")
        erppeek = dict(
            server=f"{config.get('erp_uri')}:{config.get('erp_port')}",
            db=config.get('erp_dbname'),
            user=config.get('erp_user'),
            password=config.get('erp_pwd'),
        )
        c = Client(**erppeek)
        polissa_obj = c.model("giscedata.polissa")

        found_ids = []
        for lead in lead_ids:
            if not lead.som_cups:
                continue
            polissa_id = False
            polissa_id = polissa_obj.search(
                    [('cups.name', '=ilike', '{}%'.format(lead.som_cups[:20]))]
                )
            if polissa_id:
                found_ids.append(lead.id)
                lead.write({'stage_id': self.env.ref('som_crm.som_stage_lead6').id})

        _logger.info(f"Leads moved to 'Contracted' stage: {found_ids}")
        lead_ids = lead_ids.filtered(lambda r: r.id not in found_ids)

        found_ids = []
        for lead in lead_ids:
            if not lead.vat:
                continue
            polissa_id = False
            polissa_id = polissa_obj.search(
                [('titular_nif', '=', '{}'.format(lead.vat))]
                )
            if polissa_id:
                found_ids.append(lead.id)
                lead.write({'stage_id': self.env.ref('som_crm.som_stage_lead6').id})

        _logger.info(f"Leads moved to 'Contracted' stage: {found_ids}")
        lead_ids = lead_ids.filtered(lambda r: r.id not in found_ids)
