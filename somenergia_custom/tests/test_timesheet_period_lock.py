# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta

from odoo.tests import new_test_user
from odoo.tests.common import tagged, TransactionCase
from odoo.exceptions import UserError
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT

# ─── Dates used across all tests ──────────────────────────────────────────────
LOCK_DATE = date(2026, 4, 30)     # lock boundary (inclusive)
LOCKED_DATE = date(2026, 4, 15)   # date strictly inside the locked period
OPEN_DATE = date(2026, 5, 10)     # date clearly after the lock boundary
BYPASS_FROM = date(2026, 4, 1)
BYPASS_TO = date(2026, 4, 30)


@tagged('som_timesheet_period_lock')
class TestTimesheetPeriodLock(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))

        # Company lock date
        cls.env.company.som_timesheet_lock_date = LOCK_DATE

        # Users
        # regular_user: can use timesheets, NOT a timesheet manager
        cls.regular_user = new_test_user(
            cls.env,
            login='timesheet_regular',
            groups='base.group_user,hr_timesheet.group_hr_timesheet_user',
        )
        # manager_user: has the manager group → always bypasses the lock
        cls.manager_user = new_test_user(
            cls.env,
            login='timesheet_manager',
            groups='base.group_user,hr_timesheet.group_timesheet_manager',
        )

        # Employees
        cls.employee = cls.env['hr.employee'].create({'name': 'Regular Employee'})
        cls.employee_bypass = cls.env['hr.employee'].create({
            'name': 'Bypass Employee',
            'som_lock_bypass_date_from': BYPASS_FROM,
            'som_lock_bypass_date_to': BYPASS_TO,
        })

        # Project required for account.analytic.line
        cls.project = cls.env['project.project'].create({'name': 'Lock Test Project'})

        # Calendar weeks
        cls.week_locked = cls.env['som.calendar.week'].create({
            'name': '2026-W16',
            'som_cw_code': '2026W16',
            'som_cw_date': datetime(2026, 4, 13, 0, 0, 0),
            'som_cw_date_end': datetime(2026, 4, 19, 23, 59, 59),
            'som_cw_week_number': 16,
            'som_cw_week_year': 2026,
            'som_cw_year': 2026,
        })
        cls.week_open = cls.env['som.calendar.week'].create({
            'name': '2026-W19',
            'som_cw_code': '2026W19',
            'som_cw_date': datetime(2026, 5, 4, 0, 0, 0),
            'som_cw_date_end': datetime(2026, 5, 10, 23, 59, 59),
            'som_cw_week_number': 19,
            'som_cw_week_year': 2026,
            'som_cw_year': 2026,
        })

        # Worked weeks (pre-loaded by the system, never created by end users)
        cls.worked_week_locked = cls.env['som.worked.week'].create({
            'som_week_id': cls.week_locked.id,
            'som_employee_id': cls.employee.id,
        })
        cls.worked_week_open = cls.env['som.worked.week'].create({
            'som_week_id': cls.week_open.id,
            'som_employee_id': cls.employee.id,
        })

    # ── Helper ────────────────────────────────────────────────────────────────

    def _make_line(self, date_val, employee=None, is_cumulative=False):
        """Create an account.analytic.line as admin (bypasses lock and rules)."""
        return self.env['account.analytic.line'].create({
            'name': '/',
            'project_id': self.project.id,
            'employee_id': (employee or self.employee).id,
            'date': date_val,
            'unit_amount': 1.0,
            'som_is_cumulative': is_cumulative,
        })

    # ── Group 1 — res.company._is_period_locked() ─────────────────────────────

    def test_is_period_locked_no_lock_date(self):
        """Without a lock date configured, nothing is ever locked."""
        self.env.company.som_timesheet_lock_date = False
        company = self.env.company.with_user(self.regular_user)
        self.assertFalse(company._is_period_locked(LOCKED_DATE))

    def test_is_period_locked_manager_bypasses(self):
        """Timesheet managers are never blocked, even on locked dates."""
        company = self.env.company.with_user(self.manager_user)
        self.assertFalse(company._is_period_locked(LOCKED_DATE))

    def test_is_period_locked_date_before_lock(self):
        """A date strictly before the lock boundary is locked."""
        company = self.env.company.with_user(self.regular_user)
        self.assertTrue(company._is_period_locked(LOCKED_DATE))

    def test_is_period_locked_date_at_boundary(self):
        """The lock date itself is also locked (inclusive boundary)."""
        company = self.env.company.with_user(self.regular_user)
        self.assertTrue(company._is_period_locked(LOCK_DATE))

    def test_is_period_locked_date_after_lock(self):
        """A date after the lock boundary is open."""
        company = self.env.company.with_user(self.regular_user)
        self.assertFalse(company._is_period_locked(OPEN_DATE))

    def test_is_period_locked_global_bypass_within(self):
        """Global bypass range unlocks dates falling within it."""
        self.env.company.som_timesheet_lock_bypass_date_from = BYPASS_FROM
        self.env.company.som_timesheet_lock_bypass_date_to = BYPASS_TO
        company = self.env.company.with_user(self.regular_user)
        self.assertFalse(company._is_period_locked(LOCKED_DATE))

    def test_is_period_locked_global_bypass_partial(self):
        """A partial bypass (only 'from', no 'to') does not unlock anything."""
        self.env.company.som_timesheet_lock_bypass_date_from = BYPASS_FROM
        self.env.company.som_timesheet_lock_bypass_date_to = False
        company = self.env.company.with_user(self.regular_user)
        self.assertTrue(company._is_period_locked(LOCKED_DATE))

    def test_is_period_locked_employee_bypass_within(self):
        """Per-employee bypass unlocks dates within the employee's bypass range."""
        company = self.env.company.with_user(self.regular_user)
        self.assertFalse(
            company._is_period_locked(LOCKED_DATE, employee=self.employee_bypass)
        )

    def test_is_period_locked_employee_bypass_outside(self):
        """A date outside the employee's bypass range remains locked."""
        company = self.env.company.with_user(self.regular_user)
        date_outside_bypass = date(2026, 3, 15)  # March — before bypass starts
        self.assertTrue(
            company._is_period_locked(date_outside_bypass, employee=self.employee_bypass)
        )

    # ── Group 2 — account.analytic.line.create() ──────────────────────────────

    def test_create_locked_raises(self):
        """Creating a timesheet entry in a locked period raises UserError."""
        with self.assertRaises(UserError):
            self.env['account.analytic.line'].with_user(self.regular_user).sudo().create({
                'name': '/',
                'project_id': self.project.id,
                'employee_id': self.employee.id,
                'date': LOCKED_DATE,
                'unit_amount': 1.0,
            })

    def test_create_open_ok(self):
        """Creating a timesheet entry in an open period succeeds."""
        line = self.env['account.analytic.line'].with_user(self.regular_user).sudo().create({
            'name': '/',
            'project_id': self.project.id,
            'employee_id': self.employee.id,
            'date': OPEN_DATE,
            'unit_amount': 1.0,
        })
        self.assertTrue(line)

    def test_create_cumulative_locked_ok(self):
        """System-generated cumulative lines are never blocked by the lock."""
        line = self._make_line(LOCKED_DATE, is_cumulative=True)
        self.assertTrue(line)

    def test_create_manager_locked_ok(self):
        """Timesheet managers can always create entries, even in locked periods."""
        line = self.env['account.analytic.line'].with_user(self.manager_user).sudo().create({
            'name': '/',
            'project_id': self.project.id,
            'employee_id': self.employee.id,
            'date': LOCKED_DATE,
            'unit_amount': 1.0,
        })
        self.assertTrue(line)

    def test_create_employee_bypass_ok(self):
        """Creating an entry for an employee whose bypass covers the date succeeds."""
        line = self.env['account.analytic.line'].with_user(self.regular_user).sudo().create({
            'name': '/',
            'project_id': self.project.id,
            'employee_id': self.employee_bypass.id,
            'date': LOCKED_DATE,
            'unit_amount': 1.0,
        })
        self.assertTrue(line)

    # ── Group 3 — write(): current-state check ────────────────────────────────

    def test_write_locked_record_raises(self):
        """Editing any field of a locked timesheet raises UserError."""
        line = self._make_line(LOCKED_DATE)
        with self.assertRaises(UserError):
            line.with_user(self.regular_user).sudo().write({'unit_amount': 2.0})

    def test_write_open_record_ok(self):
        """Editing a timesheet in an open period always succeeds."""
        line = self._make_line(OPEN_DATE)
        line.with_user(self.regular_user).sudo().write({'unit_amount': 2.0})
        self.assertEqual(line.unit_amount, 2.0)

    # ── Group 4 — write(): destination-state check ────────────────────────────

    def test_write_date_to_locked_raises(self):
        """Moving an open timesheet to a locked date raises UserError."""
        line = self._make_line(OPEN_DATE)
        with self.assertRaises(UserError):
            line.with_user(self.regular_user).sudo().write({'date': LOCKED_DATE})

    def test_write_employee_narrows_bypass_raises(self):
        """Switching to an employee without bypass raises UserError when date is locked."""
        # Line in locked period — OK because employee_bypass covers it
        line = self._make_line(LOCKED_DATE, employee=self.employee_bypass)
        # Switching to regular employee removes the bypass → destination state blocked
        with self.assertRaises(UserError):
            line.with_user(self.regular_user).sudo().write(
                {'employee_id': self.employee.id}
            )

    def test_write_date_to_open_ok(self):
        """Moving a timesheet to another open date always succeeds."""
        line = self._make_line(OPEN_DATE)
        new_date = OPEN_DATE + timedelta(days=1)
        line.with_user(self.regular_user).sudo().write({'date': new_date})
        self.assertEqual(line.date, new_date)

    def test_write_cumulative_date_to_locked_ok(self):
        """Cumulative lines skip the destination-state check."""
        line = self._make_line(OPEN_DATE, is_cumulative=True)
        line.write({'date': LOCKED_DATE})
        self.assertEqual(line.date, LOCKED_DATE)

    # ── Group 5 — unlink() ────────────────────────────────────────────────────

    def test_unlink_locked_raises(self):
        """Deleting a timesheet in a locked period raises UserError."""
        line = self._make_line(LOCKED_DATE)
        with self.assertRaises(UserError):
            line.with_user(self.regular_user).sudo().unlink()

    def test_unlink_open_ok(self):
        """Deleting a timesheet in an open period succeeds."""
        line = self._make_line(OPEN_DATE)
        line.with_user(self.regular_user).sudo().unlink()

    def test_unlink_cumulative_locked_ok(self):
        """Deleting a cumulative line skips the lock check."""
        line = self._make_line(LOCKED_DATE, is_cumulative=True)
        line.unlink()

    def test_remove_additional_project_unlinks_linked_locked_line(self):
        """Removing transversal link from an open line can delete a locked linked line."""
        transversal_project = self.env['project.project'].create({'name': 'Transversal Lock Test'})
        main_line = self._make_line(OPEN_DATE)
        linked_line = self._make_line(LOCKED_DATE)
        main_line.write({
            'som_additional_project_id': transversal_project.id,
            'som_timesheet_add_id': linked_line.id,
        })

        main_line.with_user(self.regular_user).sudo().write({'som_additional_project_id': False})

        linked_line_exists = self.env['account.analytic.line'].with_context(active_test=False).search([
            ('id', '=', linked_line.id),
        ])
        self.assertFalse(linked_line_exists)

    def test_unlink_open_main_line_deletes_linked_locked_line(self):
        """Deleting an open line can also delete its locked linked transversal line."""
        main_line = self._make_line(OPEN_DATE)
        linked_line = self._make_line(LOCKED_DATE)
        main_line.write({'som_timesheet_add_id': linked_line.id})

        main_line.with_user(self.regular_user).sudo().unlink()

        linked_line_exists = self.env['account.analytic.line'].with_context(active_test=False).search([
            ('id', '=', linked_line.id),
        ])
        self.assertFalse(linked_line_exists)

    # ── Group 6 — som.worked.week.write() ─────────────────────────────────────

    def test_worked_week_write_locked_raises(self):
        """Editing a worked week that falls in a locked period raises UserError."""
        with self.assertRaises(UserError):
            self.worked_week_locked.with_user(self.regular_user).sudo().write(
                {'som_employee_id': self.employee.id}
            )

    def test_worked_week_write_open_ok(self):
        """Editing a worked week in an open period succeeds."""
        self.worked_week_open.with_user(self.regular_user).sudo().write(
            {'som_employee_id': self.employee.id}
        )

    # ── Group 7 — cron ────────────────────────────────────────────────────────

    def test_cron_sets_lock_date(self):
        """Cron sets the lock date to the last day of the previous month."""
        today = date.today()
        expected_lock = today.replace(day=1) - timedelta(days=1)
        self.env['res.company']._do_update_timesheet_lock_date()
        self.assertEqual(self.env.company.som_timesheet_lock_date, expected_lock)
