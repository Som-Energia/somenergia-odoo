# -*- coding: utf-8 -*-
from psycopg2.extensions import AsIs
from odoo import fields, models, tools


class CrmLeadReport(models.Model):
    """Generate BI report based on crm.leads"""

    _name = "crm.lead.report"
    _description = "Opportunities Analysis"
    _auto = False

    id = fields.Integer(string="ID", readonly=True, index=True)
    opportunity = fields.Many2one(comodel_name="crm.lead", string="Opportunity", readonly=True)
    user_id = fields.Many2one(comodel_name="res.users", string="User", readonly=True)
    team_id = fields.Many2one(comodel_name="crm.team", string="Team", readonly=True)
    nbr_cases = fields.Integer(string="#", readonly=True)
    stage = fields.Many2one(comodel_name="crm.stage", string="State", readonly=True)
    create_date = fields.Datetime(readonly=True, index=True)
    date_closed = fields.Datetime(string="Close Date", readonly=True, index=True)
    day_close = fields.Float(string="Days to be closed", readonly=True, index=True)
    channel = fields.Many2one(comodel_name="utm.medium", string="Channel", readonly=True)
    source = fields.Many2one(comodel_name="utm.source", string="Source", readonly=True)
    lost_reason = fields.Many2one(comodel_name="crm.lost.reason", string="Lost Reason", readonly=True)
    won_daily_target = fields.Float(string="Daily target %", readonly=True, index=True)
    won_daily_target_static = fields.Integer(
        string="Daily target", readonly=True, index=True,
        group_operator="max",
    )
    virtual_state = fields.Selection(
        selection=[("w", "Won"), ("l", "Lost"), ("f", "Flying")]
    )
    count_won = fields.Integer(string="Count Won", readonly=True, index=True)
    count_flying = fields.Integer(string="Count Flying", readonly=True, index=True)
    count_lost = fields.Integer(string="Count Lost", readonly=True, index=True)
    count_total = fields.Integer(
        string="Count Total",
        group_operator="max",
        readonly=True, index=True
    )
    count_total_lost = fields.Integer(
        string="Count Total Lost",
        group_operator="max",
        readonly=True, index=True
    )
    active_stage = fields.Char(string="Active Stage", readonly=True, index=True)

    def _select(self):
        select_str = """
            select
             cl.id as id
            ,cl.id as opportunity
            ,cl.user_id
            ,cl.team_id
            ,1 as nbr_cases
            ,cl.stage_id as stage
            ,cl.create_date
            ,cl.date_closed
            ,cl.day_close
            ,cl.som_channel as channel
            ,cl.source_id as source
            ,cl.lost_reason_id as lost_reason
            ,100 / (COALESCE(
                (SELECT value FROM ir_config_parameter WHERE key = 'som_crm_daily_won_leads_target')::float,
                1.0)
            )AS won_daily_target
            ,(COALESCE(
                (SELECT value FROM ir_config_parameter WHERE key = 'som_crm_daily_won_leads_target')::integer,
                0)
            )AS won_daily_target_static
            ,case
                when cl.stage_id = (select ID from crm_stage cs where is_won = true) then 'w'
                when cl.active = false then 'l'
                else 'f'
            end as virtual_state
            ,case when cl.stage_id = (select ID from crm_stage cs where is_won = true) then 1 else 0 end as count_won
            ,case when (cl.active = true and cl.stage_id != (select ID from crm_stage cs where is_won = true)) then 1 else 0 end as count_flying
            ,case when cl.active = false then 1 else 0 end as count_lost
            ,(select count(*) from crm_lead cl) as count_total
            ,(select count(*) from crm_lead cl where active = false) as count_total_lost
            , case
                when cl.active = true then (cs2.name ->> 'ca_ES')
                else 'Perdut'
            end as active_stage
        """
        return select_str

    def _from(self):
        from_str = """
            from crm_lead cl
            left join crm_stage cs2 on cl.stage_id = cs2.id
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