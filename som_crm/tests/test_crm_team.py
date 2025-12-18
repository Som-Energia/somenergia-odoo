# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from freezegun import freeze_time
from unittest.mock import patch
from datetime import datetime


@tagged('som_crm_team')
class TestCrmTeam(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """
        Initial setup:
        - 3 Users: 1 leader, 2 members.
        - 3 Teams:
            - team_full: 3 members (including the leader).
            - team_leader_only: 1 member (who is the leader).
            - team_empty: 0 members.
        """
        super().setUpClass()

        # 1. Create Users
        cls.user_leader = cls.env['res.users'].create({
            'name': 'Test Team Leader',
            'login': 'test_leader',
            'email': 'leader@test.com',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })
        cls.user_leader_2 = cls.env['res.users'].create({
            'name': 'Test Team Leader 2',
            'login': 'test_leader_2',
            'email': 'leader2@test.com',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })
        cls.user_member_1 = cls.env['res.users'].create({
            'name': 'Test Member 1',
            'login': 'test_member1',
            'email': 'member1@test.com',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })
        cls.user_member_2 = cls.env['res.users'].create({
            'name': 'Test Member 2',
            'login': 'test_member2',
            'email': 'member2@test.com',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })

        user_ids_full = [cls.user_leader.id, cls.user_member_1.id, cls.user_member_2.id]

        # 2. Create Teams
        # Team with all members
        cls.team_full = cls.env['crm.team'].create({
            'name': 'Full Test Team',
            'user_id': cls.user_leader.id, # The team leader
            'crm_team_member_ids': [
                (0, 0, {'user_id': user_id}) for user_id in user_ids_full
            ],
        })

        # Team with only the leader
        cls.team_leader_only = cls.env['crm.team'].create({
            'name': 'Test Team (Leader Only)',
            'user_id': cls.user_leader_2.id,
            'crm_team_member_ids': [(0, 0, {'user_id': cls.user_leader_2.id})],
        })

        # Empty team
        cls.team_empty = cls.env['crm.team'].create({
            'name': 'Empty Test Team',
            'user_id': False,
            'crm_team_member_ids': False,
        })

        # employee to manage 'is_present'
        cls.user_member_1.action_create_employee()
        cls.user_member_2.action_create_employee()
        cls.user_leader.action_create_employee()
        cls.user_leader_2.action_create_employee()

        cls.hr_leave_type_1 = cls.env['hr.leave.type'].create({
            'name': 'Leave Type 1',
        })

        leave_start_datetime = datetime(2025, 4, 1, 8, 0, 0, 0)
        leave_end_datetime = datetime(2025, 4, 3, 15, 0, 0, 0)
        cls.holiday_1 = cls.env['hr.leave'].with_context(
            mail_create_nolog=True, mail_notrack=True
        ).with_user(cls.user_member_1).create({
            'name': 'Leave 1',
            'employee_id': cls.user_member_1.employee_id.id,
            'holiday_status_id': cls.hr_leave_type_1.id,
            'date_from': leave_start_datetime,
            'date_to': leave_end_datetime,
            'number_of_days': 3,
        })

    def test_empty_team(self):
        """
        Test that an empty team returns False.
        """
        member = self.team_empty.get_random_member()
        self.assertFalse(member, "An empty team should return False.")

        member_excl = self.team_empty.get_random_member(exclude_team_leader=True)
        self.assertFalse(member_excl, "An empty team (excluding leader) should return False.")

    def test_leader_only_team_include_leader(self):
        """
        Test a team with only the leader, without excluding him.
        Should return the leader.
        """
        member = self.team_leader_only.get_random_member()
        self.assertEqual(member, self.user_leader_2,
                         "It should return the leader, as he is the only member.")

    def test_leader_only_team_exclude_leader(self):
        """
        Test a team with only the leader, excluding him.
        Should return False, as the member list becomes empty.
        """
        member = self.team_leader_only.get_random_member(exclude_team_leader=True)
        self.assertFalse(member,
            "It should return False, as the only member (leader) was excluded.")

    @patch('odoo.addons.som_crm.models.crm_team.choice')
    def test_full_team_include_leader_mocked(self, mock_choice):
        """
        Test the full team, without excluding the leader, using a mock.
        Verify that 'random.choice' is called with the COMPLETE member list.
        """
        # We force 'random.choice' to return a specific member
        mock_choice.return_value = self.user_member_1

        # Call the function
        member = self.team_full.get_random_member()

        # 1. Check that the result is the one we forced
        self.assertEqual(member, self.user_member_1,
            "The returned member should be the one from the mock.")

        # 2. Check that 'random.choice' was called exactly once
        mock_choice.assert_called_once()

        # 3. (Most importantly) Check WITH WHICH list 'random.choice' was called
        #    mock_choice.call_args[0][0] is the first argument it was called with.
        called_list = mock_choice.call_args[0][0]

        self.assertEqual(len(called_list), 3,
                         "random.choice should be called with 3 members.")
        self.assertIn(self.user_leader, called_list,
                      "The leader should be in the candidate list.")
        self.assertIn(self.user_member_1, called_list,
                      "Member 1 should be in the candidate list.")

    @patch('odoo.addons.som_crm.models.crm_team.choice')
    def test_full_team_exclude_leader_mocked(self, mock_choice):
        """
        Test the full team, EXCLUDING the leader, using a mock.
        Verify that 'random.choice' is called with the FILTERED list.
        """
        # We force 'random.choice' to return a specific member
        mock_choice.return_value = self.user_member_2

        # Call the function
        member = self.team_full.get_random_member(exclude_team_leader=True)

        # 1. Check the result
        self.assertEqual(member, self.user_member_2,
                         "The returned member should be the one from the mock.")

        # 2. Check that it was called
        mock_choice.assert_called_once()

        # 3. Check the candidate list
        called_list = mock_choice.call_args[0][0]

        self.assertEqual(len(called_list), 2,
                         "random.choice should be called with only 2 members.")
        self.assertNotIn(self.user_leader, called_list,
                         "The leader should NOT be in the candidate list.")
        self.assertIn(self.user_member_1, called_list,
                      "Member 1 should be in the candidate list.")
        self.assertIn(self.user_member_2, called_list,
                      "Member 2 should be in the candidate list.")

    @freeze_time('2025-04-02 06:00:00')
    @patch('odoo.addons.som_crm.models.crm_team.choice')
    def test_team_exclude_memeber_not_is_present_mocked(self, mock_choice):
        """
        Test the full team, EXCLUDING absent members, using a mock.
        Verify that 'random.choice' is called with the FILTERED list.
        """
        # We force 'random.choice' to return a specific member
        mock_choice.return_value = self.user_member_2

        # Call the function
        member = self.team_full.get_random_member(exclude_absent_members=True)

        # 1. Check the result
        self.assertEqual(member, self.user_member_2,
                         "The returned member should be the one from the mock.")

        # 2. Check that it was called
        mock_choice.assert_called_once()

        # 3. Check the candidate list
        called_list = mock_choice.call_args[0][0]

        self.assertEqual(len(called_list), 2,
                         "random.choice should be called with only 2 members.")
        self.assertNotIn(self.user_member_1, called_list,
                         "Member 1 (absent) should NOT be in the candidate list.")
        self.assertIn(self.user_member_2, called_list,
                      "Member 2 should be in the candidate list.")

    def test_team_members_capacity(self):
        """
        Test the full team, EXCLUDING members without available leads capacity.
        Verify that only members with available capacity are considered.
        """
        # First, we set user_member_1's max leads capacity to 1
        self.user_member_2.som_max_leads_capacity = 1

        # We create an opportunity assigned to user_member_1 to fill his capacity
        self.env['crm.lead'].create({
            'name': 'Test Opportunity',
            'type': 'opportunity',
            'user_id': self.user_member_2.id,
            'team_id': self.team_full.id,
        })

        self.assertEqual(self.user_member_2._get_assigned_opportunities_count(), 1,
                         "user_member_2 should have 1 assigned opportunity.")
        self.assertEqual(self.user_member_2._get_available_leads_capacity(), 0,
                         "user_member_2 should have 0 available leads capacity.")

        # Now user_member_1 should have 0 available capacity
        member = self.team_full.get_random_member(exclude_absent_members=False)

        # The only valid member should be user_member_1 and the leader
        self.assertIn(member, [self.user_leader, self.user_member_1],
                      "The selected member should have available leads capacity.")

        # Reset to unlimited capacity
        self.user_member_2.som_max_leads_capacity = -1

        self.env['crm.lead'].create({
            'name': 'Test Opportunity 2',
            'type': 'opportunity',
            'user_id': self.user_member_2.id,
            'team_id': self.team_full.id,
        })

        self.assertEqual(self.user_member_2._get_assigned_opportunities_count(), 2,
                         "user_member_2 should have 2 assigned opportunities.")
        self.assertEqual(self.user_member_2._get_available_leads_capacity(), float('inf'),
                         "user_member_2 should have unlimited capacity.")

        member = self.team_full.get_random_member(exclude_absent_members=False)
        self.assertIn(member, [self.user_leader, self.user_member_1, self.user_member_2],
                      "With user_member_2 unlimited capacity, any member can be selected.")

    def test_team_members_capacity_no_one_available(self):
        """
        Test the full team, EXCLUDING members without available leads capacity.
        Verify that if no members have capacity, any member can be selected.
        """
        # Set all members' max leads capacity to 1
        self.user_leader.som_max_leads_capacity = 1
        self.user_member_1.som_max_leads_capacity = 1
        self.user_member_2.som_max_leads_capacity = 1
        # Create opportunities to fill their capacities
        for user in [self.user_leader, self.user_member_1, self.user_member_2]:
            self.env['crm.lead'].create({
                'name': f'Test Opportunity for {user.name}',
                'type': 'opportunity',
                'user_id': user.id,
                'team_id': self.team_full.id,
            })
            self.assertEqual(user._get_available_leads_capacity(), 0,
                             f"{user.name} should have 0 available leads capacity.")
        # Now, all members have 0 available capacity
        member = self.team_full.get_random_member(exclude_absent_members=False)
        self.assertIn(member, [self.user_leader, self.user_member_1, self.user_member_2],
                      "With no available capacity, any member can be selected.")
