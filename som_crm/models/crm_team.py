# -*- coding: utf-8 -*-
from random import choice
from odoo import models, api, _
from odoo.exceptions import UserError

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    def get_random_member(self, exclude_team_leader=False, exclude_absent_members=True):
        """ Returns a random member of the sales team. """
        self.ensure_one()
        user_member_ids = self.member_ids
        if exclude_team_leader:
            user_member_ids = self.member_ids.filtered(lambda x: x != self.user_id)
        if exclude_absent_members:
            user_member_ids = user_member_ids.filtered(lambda x: x.employee_id.is_present)
        if not user_member_ids:
            return False
        random_member_id = choice(user_member_ids)
        return random_member_id
