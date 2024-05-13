# -*- coding: utf-8 -*-

from psycopg2.extensions import AsIs
from odoo import fields, models, tools

AVAILABLE_STATES = [
    ("draft", "Draft"),
    ("open", "Todo"),
    ("cancel", "Cancelled"),
    ("done", "Held"),
    ("pending", "Pending"),
]


class CrmPhonecallReport(models.Model):
    """Generate BI report based on phonecall."""

    _inherit = "crm.phonecall.report"

    som_operator = fields.Char(
        string="Operator", readonly=True
    )
    som_caller_name = fields.Char(
        string="Caller name", readonly=True
    )
    som_contract_name = fields.Char(
        string="Contract name", readonly=True
    )

    category_name = fields.Char(
        string="Category", readonly=True
    )
    category_fullcode = fields.Char(
        string="Category code", readonly=True
    )

    total_calls = fields.Integer(
        string="Total calls", readonly=True,
        group_operator="max",
    )

    category_l0_name = fields.Char(
        string="Category Level0", readonly=True
    )
    category_l0_fullcode = fields.Char(
        string="Category Level0 code", readonly=True
    )

    category_l1_name = fields.Char(
        string="Category Level1", readonly=True
    )
    category_l1_fullcode = fields.Char(
        string="Category Level1 code", readonly=True
    )

    category_l2_name = fields.Char(
        string="Category Level2", readonly=True
    )
    category_l2_fullcode = fields.Char(
        string="Category Level2 code", readonly=True
    )

    def _select(self):
        # select_str = super()._select()
        select_str = """
                select
                    c.id,
                    c.date_open AS opening_date,
                    c.date_closed,
                    c.state,
                    c.user_id,
                    c.team_id,
                    c.partner_id,
                    c.duration,
                    c.company_id,
                    c.priority,
                    1 AS nbr_cases,
                    c.create_date,
                    EXTRACT(epoch FROM c.date_closed - c.create_date) / (3600 * 24)::numeric AS delay_close,
                    EXTRACT(epoch FROM c.date_open - c.create_date) / (3600 * 24)::numeric AS delay_open,
                    c.som_operator,
                    c.som_caller_name,
                    c.som_contract_name,
                    pc.complete_name as category_name,
                    pc.som_full_code as category_fullcode,
                    (select count(*) from crm_phonecall) as total_calls,
                    pc_l0.complete_name as category_l0_name,
                    pc_l0.som_full_code as category_l0_fullcode,
                    pc_l1.complete_name as category_l1_name,
                    pc_l1.som_full_code as category_l1_fullcode,
                    pc_l2.complete_name as category_l2_name,
                    pc_l2.som_full_code as category_l2_fullcode
                    """
        return select_str

    def _from(self):
        select_str = super()._from()
        select_str += """
                    left join som_call_category_rel sccr on c.id = sccr.call_id
                    left join product_category pc on pc.id = sccr.category_id
                    left join product_category pc_l0 on pc.som_ancestor_level0 = pc_l0.id
                    left join product_category pc_l1 on pc.som_ancestor_level1 = pc_l1.id
                    left join product_category pc_l2 on pc.som_ancestor_level2 = pc_l2.id
                    """
        return select_str
