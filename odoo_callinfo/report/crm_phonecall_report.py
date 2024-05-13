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
                    (select count(*) from crm_phonecall) as total_calls
                    """
        return select_str

    def _from(self):
        select_str = super()._from()
        select_str += """
                    left join som_call_category_rel sccr on c.id = sccr.call_id
                    left join product_category pc on pc.id = sccr.category_id
                    """
        return select_str
