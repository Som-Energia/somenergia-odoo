# -*- coding: utf-8 -*-
from psycopg2.extensions import AsIs

from odoo import fields, models, tools, api


class HrAttendanceOverlappingReport(models.Model):
    """Generate report based on sql view."""

    _name = "hr.attendance.overlapping.report"
    _description = "Attendance Overlapping Report"
    _auto = False

    absence_id = fields.Many2one(comodel_name="hr.leave", string="Absence", readonly=True)
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", readonly=True)
    absence_type = fields.Char(string="Absence Type", readonly=True)
    absence_full_day = fields.Boolean(string="Absence Full Day", readonly=True)
    absence_state = fields.Char(string="Absence State", readonly=True)
    absence_from = fields.Datetime(readonly=True, index=True)
    absence_to = fields.Datetime(readonly=True, index=True)
    check_in = fields.Datetime(readonly=True, index=True)
    check_out = fields.Datetime(readonly=True, index=True)

    @api.model
    def _select(self):
        select_str = """
            select 
            hl.id,
            hl.id as absence_id,
            he.id as employee_id,
            hlt."name" ->> 'en_US' as absence_type,
            (hl.request_unit_half = false and hl.request_unit_hours = false) as absence_full_day,
            hl.state as absence_state,
            hl.date_from as absence_from,
            hl.date_to as absence_to,
            ha.check_in as check_in,
            ha.check_out as check_out
           """
        return select_str

    @api.model
    def _from(self):
        from_str = """
            from hr_leave hl
            inner join hr_employee he on he.id = hl.employee_id
            inner join hr_leave_type hlt on hlt.id = hl.holiday_status_id
            inner join hr_attendance ha on
                hl.employee_id = ha.employee_id
                and
                hl.employee_id = ha.employee_id
                and
                (
                    (--partial day
                        (hl.request_unit_half = true or hl.request_unit_hours = true)
                        and
                        (
                            (hl.date_from < ha.check_in and ha.check_in < hl.date_to)
                              or
                            (hl.date_from < ha.check_out and ha.check_out < hl.date_to)
                              or
                            (ha.check_in < hl.date_from and hl.date_to < ha.check_out)
                        )
                    )
                    or
                    (--full day
                        (hl.request_unit_half = false and hl.request_unit_hours = false)
                        and 
                        (
                            (hl.request_date_from <= date(ha.check_in) and date(ha.check_in) <= hl.request_date_to)
                              or
                            (hl.request_date_from <= date(ha.check_out) and date(ha.check_out) <= hl.request_date_to)
                              or
                            (date(ha.check_in) <= hl.request_date_from and hl.request_date_to <= date(ha.check_out))
                        )
                    )
                )
        """
        return from_str

    @api.model
    def _where(self):
        return '''
                where
                hl.state in ('confirm', 'validate') and hl.active = true
            '''

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
            (AsIs(self._table), AsIs(self._select()), AsIs(self._from()), AsIs(self._where())),
        )
