# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import datetime, timedelta

class HrHolidaysPublicLine(models.Model):
    _inherit = "hr.holidays.public.line"

    # Function to get the list of dates between two dates
    @api.model
    def _get_dates_between(self, start_date, end_date):
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date)
            current_date += timedelta(days=1)
        return date_list

    @api.model
    def get_festivities(self, start_date, end_date):
        """
        This function returns festivities (Public holidays) from start_date to end_date in the following
        format: {'date': '2024-01-01', 'name': 'Any nou'}
        """
        res = []
        search_params = [
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ]
        public_holiday_ids = self.env['hr.holidays.public.line'].search(search_params)

        for ph_id in public_holiday_ids:
            res.append({
                'date': ph_id.date,
                'name': ph_id.name,
            })

        # get from stress_days without departments
        sd_leave_ids = self.env['hr.leave.stress.day'].search([
            ('start_date', '>=', start_date),
            ('end_date', '<=', end_date),
            ('som_type', '=', 'no_service'),
            ('department_ids', '=', False),
        ])

        for sd_leave_id in sd_leave_ids:
            # Get the dates between start_date and end_date
            dates = self._get_dates_between(sd_leave_id.start_date, sd_leave_id.end_date)
            for date in dates:
                res.append({
                    'date': date,
                    'name': sd_leave_id.name,
                })

        return res
