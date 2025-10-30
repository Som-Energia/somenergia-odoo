# -*- coding: utf-8 -*-
from psycopg2.extensions import AsIs
from odoo import fields, models, tools


class CrmLeadReport(models.Model):
    """Generate BI report based on crm.leads"""

    _name = "crm.lead.report"
    _description = "Opportunities Analysis"
    _auto = False

    id = fields.Integer(string="Id", readonly=True, index=True)
    user_id = fields.Many2one(comodel_name="res.users", string="User", readonly=True)
    team_id = fields.Many2one(comodel_name="crm.team", string="Team", readonly=True)
    nbr_cases = fields.Integer(string="#", readonly=True)
    state = fields.Many2one(comodel_name="crm.stage", string="State", readonly=True)
    create_date = fields.Datetime(readonly=True, index=True)
    date_closed = fields.Datetime(string="Close Date", readonly=True, index=True)
    day_close = fields.Float(string="Days to be closed", readonly=True, index=True)
    won_daily_target = fields.Integer(string="Daily target", readonly=True, index=True)

    def _select(self):
        select_str = """
            select
             cl.id as id
            ,cl.user_id
            ,cl.team_id
            ,1 as nbr_cases
            ,cl.stage_id as state
            ,cl.create_date
            ,cl.date_closed
            ,cl.day_close
            ,COALESCE(
                (SELECT value FROM ir_config_parameter WHERE key = 'som_crm_daily_won_leads_target')::integer,
                0
            )AS won_daily_target
        """
        return select_str

    def _from(self):
        from_str = """
            from crm_lead cl
        """
        return from_str

    def _where(self):
        return """
        """

    def init(self):
        """Initialize the report."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            create or replace view %s as (
                %s
                %s
                %s
            )""",
            (
                AsIs(self._table),
                AsIs(self._select()),
                AsIs(self._from()),
                AsIs(self._where())
            ),
        )
