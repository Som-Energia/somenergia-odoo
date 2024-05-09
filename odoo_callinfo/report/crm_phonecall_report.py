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
        string="Operator",
    )
    som_caller_name = fields.Char(
        string="Caller name",
    )
    som_contract_name = fields.Char(
        string="Contract name",
    )

    cat_1_name = fields.Char(
        string="Cat1 Name",
    )
    cat_1_fullcode = fields.Char(
        string="Cat1 FullCode",
    )

    cat_2_name = fields.Char(
        string="Cat2 Name",
    )
    cat_2_fullcode = fields.Char(
        string="Cat2 FullCode",
    )

    def _select(self):
        select_str = super()._select()
        select_str += """
                    , c.som_operator
                    , c.som_caller_name
                    , c.som_contract_name
                    , sq_cat_1.complete_name as cat_1_name
                    , sq_cat_1.som_full_code as cat_1_fullcode
                    , sq_cat_2.complete_name as cat_2_name
                    , sq_cat_2.som_full_code as cat_2_fullcode
                    """
        return select_str

    def _from(self):
        select_str = super()._from()
        select_str += """
                    left join 
                   (
                    select * from 
                    (
                        select 
                        ROW_NUMBER () OVER (
                            PARTITION BY sccr.call_id 
                        ) as rn	
                        ,sccr.*,pc.complete_name, pc.som_full_code
                        from som_call_category_rel sccr
                        left join product_category pc ON pc.id = sccr.category_id 
                    )sq where rn = 1
                   ) as sq_cat_1 on sq_cat_1.call_id = c.id 
                   left join
                   (
                    select * from 
                    (
                        select 
                        ROW_NUMBER () OVER (
                            PARTITION BY sccr.call_id 
                        ) as rn	
                        ,sccr.*,pc.complete_name, pc.som_full_code
                        from som_call_category_rel sccr
                        left join product_category pc ON pc.id = sccr.category_id 
                    )sq where rn = 2
                   ) as sq_cat_2 on sq_cat_2.call_id = c.id
                    """
        return select_str
