# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    som_restrictive_stress_days = fields.Boolean(
        string="Restrictive stress days",
        default=True,
    )

    som_restrictive_overtime = fields.Boolean(
        string="Restrictive overtime",
        default=False,
    )

    som_amend_attendance_restrictive = fields.Boolean(
        string="Restrictive amend attendance",
        default=False,
    )

    som_amend_attendance_days_to = fields.Integer(
        string="Days to amend attendance",
        default=1,
    )

    som_attendance_limit_checkin = fields.Float(
        digits=(2, 2), default=6.0
    )

    som_attendance_limit_checkout = fields.Float(
        digits=(2, 2), default=22.0
    )

    som_timesheet_lock_date = fields.Date(
        string="Timesheet lock date",
    )

    som_timesheet_lock_bypass_date_from = fields.Date(
        string="Global bypass from",
    )

    som_timesheet_lock_bypass_date_to = fields.Date(
        string="Global bypass to",
    )

    def _is_period_locked(self, date_to_check, employee=None):
        """Returns True if date_to_check falls within a locked period.

        Managers are always allowed.
        Global bypass and per-employee bypass use date ranges (both dates must be set).
        date_to_check can be a date, datetime or 'YYYY-MM-DD' string.
        """
        self.ensure_one()
        if not self.som_timesheet_lock_date:
            return False
        if self.env.user.has_group('hr_timesheet.group_timesheet_manager'):
            return False
        # Normalize date_to_check
        if isinstance(date_to_check, str):
            date_to_check = fields.Date.from_string(date_to_check)
        elif hasattr(date_to_check, 'date'):
            date_to_check = date_to_check.date()
        # Global bypass: active only if both dates are set and date falls within range
        bypass_from = self.som_timesheet_lock_bypass_date_from
        bypass_to = self.som_timesheet_lock_bypass_date_to
        if bypass_from and bypass_to and bypass_from <= date_to_check <= bypass_to:
            return False
        # Per-employee bypass: same logic
        if employee:
            emp_bypass_from = employee.som_lock_bypass_date_from
            emp_bypass_to = employee.som_lock_bypass_date_to
            if emp_bypass_from and emp_bypass_to and emp_bypass_from <= date_to_check <= emp_bypass_to:
                return False
        return date_to_check <= self.som_timesheet_lock_date

    @api.model
    def _do_update_timesheet_lock_date(self):
        """Cron: estableix la data de tancament a l'últim dia del mes anterior."""
        first_day_current = fields.Date.today().replace(day=1)
        last_day_prev = first_day_current - timedelta(days=1)
        companies = self.sudo().search([])
        for company in companies:
            company.sudo().som_timesheet_lock_date = last_day_prev
        _logger.info("Timesheet lock date updated to %s", last_day_prev)
