# -*- coding: utf-8 -*-
from random import choice
from odoo import models, fields
from odoo.exceptions import UserError

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    def get_random_member(self, exclude_team_leader=False, exclude_absent_members=True):
        """ Returns a random member of the sales team. """
        self.ensure_one()
        today = fields.Date.context_today(self)

        def _can_be_assigned_opportunities(user):
            if not user.som_not_assign_opportunities:
                return True
            from_date = user.som_not_assign_opportunities_from
            to_date = user.som_not_assign_opportunities_to
            if not from_date or not to_date:
                return False
            return not (from_date <= today <= to_date)

        user_member_ids = self.member_ids
        if exclude_team_leader:
            user_member_ids = user_member_ids.filtered(lambda x: x != self.user_id)
        if exclude_absent_members:
            user_member_ids = user_member_ids.filtered(lambda x: x.employee_id.is_present)
        user_member_ids = user_member_ids.filtered(_can_be_assigned_opportunities)
        user_member_with_capacity_ids = user_member_ids.filtered(
            lambda x: x._get_available_leads_capacity() > 0
        )
        if not user_member_ids:
            return False
        if user_member_with_capacity_ids:
            random_member_id = choice(user_member_with_capacity_ids)
        else:
            random_member_id = choice(user_member_ids)
        return random_member_id
