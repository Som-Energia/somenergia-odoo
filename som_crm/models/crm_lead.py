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

    @api.model
    def _erp_connect(self):
        erppeek = dict(
            server=f"{config.get('erp_uri')}:{config.get('erp_port')}",
            db=config.get('erp_dbname'),
            user=config.get('erp_user'),
            password=config.get('erp_pwd'),
        )
        c = Client(**erppeek)

        obj_res_partner = c.model("res.partner")
        partner_id = obj_res_partner.browse(37577)
        print(partner_id.name)

        pass
