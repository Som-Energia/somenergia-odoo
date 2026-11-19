# -*- coding: utf-8 -*-
from random import choice
from odoo import models, fields
from odoo.exceptions import UserError

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    def get_random_member(self, exclude_team_leader=False, exclude_absent_members=True):
        """ Returns a random member of the sales team. """
        self.ensure_one()
        user_member_ids = self.member_ids
        if exclude_team_leader:
            user_member_ids = user_member_ids.filtered(lambda x: x != self.user_id)
        return self._get_random_assignable_member(
            user_member_ids, exclude_absent_members=exclude_absent_members,
        )

    def _get_random_assignable_member(self, user_member_ids, exclude_absent_members=True,
                                      approved_leaves_only=False):
        """Select only from the supplied pool; preserve the web selection policy."""
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

        if exclude_absent_members:
            leave_domain = [
                ('employee_id', 'in', user_member_ids.mapped('employee_id').ids),
                ('request_date_from', '<=', today),
                ('request_date_to', '>=', today),
            ]
            if approved_leaves_only:
                leave_domain.append(('state', '=', 'validate'))
            absent_today_employee_ids = set(
                self.env['hr.leave'].sudo().search(leave_domain).mapped('employee_id').ids)
            user_member_ids = user_member_ids.filtered(
                lambda x: x.employee_id and x.employee_id.id not in absent_today_employee_ids
            )
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
