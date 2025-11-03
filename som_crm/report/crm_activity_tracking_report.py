# -*- coding: utf-8 -*-
from psycopg2.extensions import AsIs
from odoo import fields, models, tools


class CrmActivityTrackingReport(models.Model):
    """Generate BI report based on mail.activity and mail.message"""

    _name = "crm.activity.tracking.report"
    _description = "Activities Analysis"
    _auto = False

    id = fields.Integer(string="ID", readonly=True, index=True)
    nbr_cases = fields.Integer(string="#", readonly=True)
    user = fields.Many2one(comodel_name="res.users", string="User", readonly=True)
    activity_state = fields.Selection(
        selection=[("done", "Done"), ("pending", "Pending")]
    )
    date = fields.Datetime(string="Date", readonly=True, index=True)
    opportunity = fields.Many2one(comodel_name="crm.lead", string="Opportunity", readonly=True)
    activity_type = fields.Many2one(
        comodel_name="mail.activity.type", string="Activity Type", readonly=True)

    def _select(self):
        select_str = """
        select
            1 as nbr_cases
            ,*
        from
        (
            select mm.id, 'done' as activity_state, ru.id as user, date as date
            ,res_id as opportunity
            ,mm.mail_activity_type_id as activity_type
            from mail_message mm
            left join res_users ru on ru.partner_id = mm.author_id
            where mm.subtype_id = 3 and mm.model = 'crm.lead'

            union all

            select ma.id, 'pending' as activity_state, user_id as user, date_deadline as date
            ,res_id as opportunity
            ,ma.activity_type_id as activity_type
            from mail_activity ma
            where res_model = 'crm.lead'
        ) sq_activity
        """
        return select_str

    def _from(self):
        from_str = """
        """
        return from_str

    def _where(self):
        where_str = """

        """
        return where_str

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
