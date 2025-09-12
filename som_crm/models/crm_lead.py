# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from erppeek import Client
from odoo.tools import config


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

    def get_leads_to_update(self):

        searchable_stages = [
            "Pending 1st contact",
            "Pending 1st contact and simulation",
            "Pending simulation or comparison",
            "Simulation or comparison sent",
            "Interested and will contract",
        ]
        crm_stage_ids = self.env['crm.stage'].search([('name', 'in', searchable_stages)])

        return self.search(
            [
                ("stage_id", "in", crm_stage_ids.ids),

            ]
        )

    @api.model
    def _erp_connect(self):

        lead_ids = self.get_leads_to_update()
        print(f"leads to update: {lead_ids}")
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

        print(f"Leads moved to 'Contracted' stage: {found_ids}")
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

        print(f"Leads moved to 'Contracted' stage: {found_ids}")
        lead_ids = lead_ids.filtered(lambda r: r.id not in found_ids)
