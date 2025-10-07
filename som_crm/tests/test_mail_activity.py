 # -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import date


@tagged('som_mail_activity')
class TestMailActivity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        # sales_team.group_sale_salesman_all_leads

        """ Prepare common data for all test methods. """
        super().setUpClass()
        # Disable tracking for performance and consistency
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # 1. Create Call Center user (assuming it has a som_call_center_user field)
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test Call Center User',
            'login': 'test_cc_user',
            'email': 'test@ccuser.com',
            'som_call_center_user': 'call_center_1',
            "groups_id": [
                (6, 0, [cls.env.ref("sales_team.group_sale_salesman_all_leads").id])
            ],
        })

        # 2. Create a 'Phonecall' activity type
        cls.activity_type_phonecall = cls.env.ref(
            'mail.mail_activity_data_call', raise_if_not_found=False
        )
        if cls.activity_type_phonecall.category != 'phonecall':
            cls.activity_type_phonecall.write({'category': 'phonecall'})

        # 3. Create the phone call result model and test records
        # Assuming 'phone.call.result' exists in your module or a dependency.
        cls.phone_call_result_model = cls.env['phone.call.result']
        cls.result_done = cls.phone_call_result_model.create({'name': 'Successfully Contacted'})
        cls.result_no_answer = cls.phone_call_result_model.create({'name': 'No Answer'})

        # 4. Create a Lead/Opportunity (the resource record for the activity)
        cls.test_lead = cls.env['crm.lead'].create({
            'name': 'Test Lead for Phone Call',
            'phone': '123456789',
            'partner_id': cls.env['res.partner'].create({'name': 'Test Partner'}).id,
        })

        # 5. Create a Phonecall activity for testing
        cls.activity_phonecall = cls.env['mail.activity'].create({
            'res_model_id': cls.env['ir.model']._get('crm.lead').id,
            'res_id': cls.test_lead.id,
            'activity_type_id': cls.activity_type_phonecall.id,
            'summary': 'Scheduled Phone Call for Lead',
            'user_id': cls.test_user.id,
            'date_deadline': date.today(),
            'activity_category': 'phonecall',
        })

        # 6. Create a non-phonecall activity to test the standard Odoo flow
        cls.activity_meeting = cls.env['mail.activity'].create({
            'res_model_id': cls.env['ir.model']._get('crm.lead').id,
            'res_id': cls.test_lead.id,
            'activity_type_id': cls.env.ref('mail.mail_activity_data_meeting').id,
            'summary': 'Scheduled Meeting',
            'user_id': cls.test_user.id,
            'date_deadline': date.today(),
            'activity_category': 'meeting',
        })

    # -------------------------------------------------------------------------
    # Test Scenarios
    # -------------------------------------------------------------------------

    def test_phonecall_done_success_with_feedback(self):
        """ Test _action_done on a Phonecall activity with result and custom feedback.
            It should create a crm.phonecall record and update the chatter message.
        """

        # Prepare the activity with the required fields
        self.activity_phonecall.write({
            'som_phone_call_result_id': self.result_done.id,
            'som_phone_call_duration': 5.5,
            'note': 'The lead was very interested.',
        })

        initial_feedback = "Discussion notes: very positive."

        # Mark as done (calls the overridden _action_done)
        self.activity_phonecall.with_user(self.test_user)._action_done(feedback=initial_feedback)

        # Check if the activity was marked as done (deleted/archived, depending on base config)
        self.assertFalse(
            self.activity_phonecall.exists(),
            "The activity should have been marked as done and deleted."
        )

        # Check that a crm.phonecall record was created
        phonecall = self.env['crm.phonecall'].search([('opportunity_id', '=', self.test_lead.id)], limit=1)
        self.assertTrue(phonecall, "crm.phonecall record was not created.")

        # Check crm.phonecall field values
        self.assertEqual(
            phonecall.som_phone_call_result_id.id, self.result_done.id,
            "The phone call result is incorrect."
        )
        self.assertEqual(phonecall.duration, 5.5, "The phone call duration is incorrect.")
        self.assertEqual(phonecall.state, 'done', "The phone call state is not 'done'.")
        self.assertEqual(
            phonecall.som_operator, 'call_center_1', "The som_operator field is not True."
        )
        self.assertEqual(phonecall.som_phone, '123456789', "The phone number is incorrect.")

        # Check the Chatter Message on the Lead (feedback must contain the result name)
        message = self.test_lead.message_ids.sorted('date', reverse=True)[0]
        expected_part = "<strong>Phone Call Result: </strong> Successfully Contacted"
        self.assertIn(
            expected_part, message.body,
            "The phone call result was not added to the Chatter feedback."
        )
        self.assertIn(initial_feedback, message.body, "The original feedback was not preserved.")

    def test_phonecall_done_success_without_feedback(self):
        """ Test _action_done on a Phonecall activity with a result, but without custom feedback.
            It should create a crm.phonecall record and the chatter message should only contain the result.
        """

        # Prepare the activity with required fields
        self.activity_phonecall_2 = self.activity_phonecall.copy({
            'som_phone_call_result_id': self.result_no_answer.id,
            'som_phone_call_duration': 0.1,
            'note': False,
        })

        # Mark as done (calls the overridden _action_done)
        self.activity_phonecall_2.with_user(self.test_user)._action_done(feedback=False)

        # Check crm.phonecall creation
        phonecall = self.env['crm.phonecall'].search([
            ('som_phone_call_result_id', '=', self.result_no_answer.id)
        ], limit=1)
        self.assertTrue(phonecall, "The second crm.phonecall record was not created.")

        # Check the Chatter Message (should only contain the result name)
        message = self.test_lead.message_ids.sorted('date', reverse=True)[0]
        expected_body = f"<strong>Phone Call Result: </strong>{self.result_no_answer.name}"
        self.assertIn(
            expected_body, message.body, "Only the phone call result should be the feedback."
        )

    def test_phonecall_done_required_field_check(self):
        """ Test _action_done on a Phonecall activity without som_phone_call_result_id raises ValidationError. """

        # The 'som_phone_call_result_id' field is empty
        self.activity_phonecall_3 = self.activity_phonecall.copy({
            'som_phone_call_result_id': False,
            'som_phone_call_duration': 3.0,
            'note': 'This should fail.',
        })

        # Try to mark as done and expect the error
        with self.assertRaises(
            ValidationError, msg="A validation error was expected for the missing required field."
        ):
            self.activity_phonecall_3.with_user(self.test_user)._action_done()

        # Check that the activity was NOT marked as done (should still exist)
        self.assertTrue(
            self.activity_phonecall_3.exists(),
            "The activity should not have been marked as done after the error."
        )

    def test_non_phonecall_activity_done(self):
        """ Test _action_done on a non-phonecall activity follows the normal Odoo flow
            and does not create a crm.phonecall record.
        """

        # Create a new lead to isolate the crm.phonecall count
        test_lead_2 = self.env['crm.lead'].create({'name': 'Test Lead 2', 'phone': '999'})

        # Copy the meeting activity to the new lead
        activity_meeting_copy = self.activity_meeting.copy({'res_id': test_lead_2.id})

        # Initial crm.phonecall count for this lead
        initial_phonecall_count = self.env['crm.phonecall'].search_count([
            ('opportunity_id', '=', test_lead_2.id)
        ])

        # Mark as done (should call super() and skip the custom logic)
        activity_meeting_copy.with_user(self.test_user)._action_done(
            feedback="Meeting was successful."
        )

        # Check if the activity was marked as done
        self.assertFalse(
            activity_meeting_copy.exists(), "The Meeting activity should have been marked as done."
        )

        # Final crm.phonecall count
        final_phonecall_count = self.env['crm.phonecall'].search_count([
            ('opportunity_id', '=', test_lead_2.id)
        ])

        # Check that a crm.phonecall record was NOT created
        self.assertEqual(
            initial_phonecall_count,
            final_phonecall_count,
            "A crm.phonecall should not be created for a non-'phonecall' activity."
        )

    def test_phonecall_done_non_crm_model(self):
        """ Test _action_done on a Phonecall activity, but associated with a non-'crm.lead' model (e.g., res.partner).
            It should be marked as done but should not create a crm.phonecall record.
        """

        phonecall_count_pre = self.env['crm.phonecall'].search_count([])

        # Create a Partner to use as the resource
        test_partner = self.env['res.partner'].create({'name': 'Test Partner for Phone Call'})

        # Create the activity associated with the partner
        activity_partner_phonecall = self.activity_phonecall.copy({
            'res_model_id': self.env['ir.model']._get('res.partner').id,
            'res_id': test_partner.id,
            'som_phone_call_result_id': self.result_done.id,
            'activity_category': 'phonecall',
        })

        # Mark as done (should be marked as done, but skip the crm.phonecall creation logic)
        activity_partner_phonecall.with_user(self.test_user)._action_done(
            feedback="Called partner."
        )

        # Check if the activity was marked as done
        self.assertFalse(
            activity_partner_phonecall.exists(),
            "The activity on res.partner should have been marked as done."
        )

        # Check that a crm.phonecall record was NOT created
        phonecall_count_post = self.env['crm.phonecall'].search_count([])
        self.assertEqual(
            phonecall_count_pre,
            phonecall_count_post,
            "A crm.phonecall should not be created for a non-'crm.lead' model."
        )
