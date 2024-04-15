# -*- coding: utf-8 -*-
import uuid
from logging import getLogger
from odoo import api, fields, models, exceptions, _
from odoo.modules.module import get_module_resource

_logger = getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    name = fields.Char(
        default="/"
    )

    som_worked_week_id = fields.Many2one(
        comodel_name="som.worked.week",
        string="Worked week",
    )

    som_week_id = fields.Many2one(
        comodel_name="som.calendar.week",
        string="Week"
    )

    som_is_cumulative = fields.Boolean(
        string="Is cumulative"
    )

    som_project_area_domain_ids = fields.Many2many(
        "project.project",
        store=False,
    )

    som_additional_project_domain_ids = fields.Many2many(
        "project.project",
        store=False,
    )

    som_additional_project_id = fields.Many2one(
        comodel_name="project.project",
        string="Transversal project"
    )

    som_additional_project_task_id = fields.Many2one(
        comodel_name="project.task",
        string="Transversal task"
    )

    som_timesheet_add_id = fields.Many2one(
        comodel_name="account.analytic.line",
        string="Linked timesheet"
    )

    som_timesheet_uuid_hook = fields.Char(
        string="Timesheet UUID Hook",
    )

    def _match_timesheets(self, timesheet_ids):
        list_uuid = list(set(timesheet_ids.mapped('som_timesheet_uuid_hook')))
        for str_uuid in list_uuid:
            linked_timesheet_ids = timesheet_ids.filtered(
                lambda x: x.som_timesheet_uuid_hook == str_uuid and not x.som_timesheet_add_id
            )
            if len(linked_timesheet_ids) == 2:
                timesheet_week_ids = linked_timesheet_ids.filtered(lambda x: x.som_worked_week_id)
                timesheet_add_ids = linked_timesheet_ids.filtered(lambda x: not x.som_worked_week_id)
                timesheet_week_id = timesheet_week_ids[0] if len(timesheet_week_ids) > 0 else False
                timesheet_add_id = timesheet_add_ids[0] if len(timesheet_add_ids) > 0 else False
                if timesheet_week_id and timesheet_add_id:
                    timesheet_week_id.som_timesheet_add_id = timesheet_add_id.id

    def unlink(self):
        for record in self:
            if record.som_is_cumulative:
                return False
            if record.som_worked_week_id and record.som_timesheet_add_id:
                record.som_timesheet_add_id.unlink()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        flag_match = False
        for values in vals_list:
            if values.get('som_additional_project_id', False):
                str_uuid = str(uuid.uuid4()).replace('-', '')
                id_project_transversal = values.get('som_additional_project_id', False)
                dict_vals_transversal_timesheet = {
                    key: value for key, value in values.items() if key not in [
                        'som_additional_project_id',
                        'som_worked_week_id',
                        'som_week_id',
                    ]
                }
                dict_vals_transversal_timesheet.update({
                    'project_id': id_project_transversal,
                    'som_timesheet_uuid_hook': str_uuid,
                })
                values['som_timesheet_uuid_hook'] = str_uuid
                vals_list.append(dict_vals_transversal_timesheet)
                flag_match = True
        res = super(AccountAnalyticLine, self).create(vals_list)
        if flag_match:
            self._match_timesheets(res)
        return res

    def write(self, vals):
        if vals.get('unit_amount'):
            for record in self:
                if record.som_worked_week_id and record.som_timesheet_add_id:
                    record.som_timesheet_add_id.unit_amount = vals.get("unit_amount")
        if vals.get('som_additional_project_id'):
            for record in self:
                if record.som_timesheet_add_id:
                    # change project of linked timesheet
                    record.som_timesheet_add_id.project_id = vals.get('som_additional_project_id')
                else:
                    # create linked timesheet and link them
                    som_timesheet_add_id = record.copy()
                    som_timesheet_add_id.write({
                        'som_additional_project_id': False,
                        'som_worked_week_id': False,
                        'som_week_id': False,
                        'project_id': vals.get('som_additional_project_id'),
                        'unit_amount': vals.get('unit_amount', record.unit_amount)
                    })
                    record.som_timesheet_add_id = som_timesheet_add_id.id
        if 'som_additional_project_id' in vals and not vals.get('som_additional_project_id'):
            timesheet_ids = self.env['account.analytic.line'].search([
                ('som_worked_week_id', '!=', False),
                ('project_id', '!=', False),
            ])
            # remove linked timesheet
            for record in self:
                if record.som_timesheet_add_id and record.som_timesheet_add_id.id not in timesheet_ids.ids:
                    record.som_timesheet_add_id.unlink()

        return super().write(vals)

    @api.onchange('som_week_id')
    def onchange_week(self):
        self.date = (
            self.som_week_id.som_cw_date.date() if self.som_week_id else False
        )

    def _get_cumulative_timesheet_week(self, employee_id, year):
        query_name = "query_get_wh_employee_by_weeek.sql"
        query_file = get_module_resource(
            "somenergia_custom", "query", query_name
        )
        query = open(query_file).read()
        cr = self.env.cr
        result = []
        cr.execute(
            query, (
                employee_id.id, employee_id.id,
                year, year
            )
        )
        result = cr.fetchall()
        return result

    @api.model
    def _do_load_wh_week_timesheets_current_user(self):
        year = fields.Date.today().year
        list_employee = []
        if not self.env.user._is_admin():
            list_employee.append(self.env.user.employee_id.id)
        self._do_load_wh_week_timesheets(year, list_employee)

    @api.model
    def _do_load_wh_week_timesheets(self, year, list_employee=[]):
        _logger.info('START - _do_load_wh_week_timesheets')
        project_ch_id = self.env.ref(
            'somenergia_custom.som_cumulative_hours_project'
        )

        domain = []
        if list_employee:
            domain = [('id', 'in', list_employee)]

        employee_ids = self.env['hr.employee'].search(domain)
        for employee_id in employee_ids:
            _logger.info("loading employee '[%s] %s'" % (employee_id.id, employee_id.name))
            worked_hours = self._get_cumulative_timesheet_week(employee_id, year)
            for worked_week in worked_hours:
                id_week = worked_week[0]
                week_name = worked_week[1]
                week_date = worked_week[2].date()
                worked_hours = round(worked_week[4], 2)

                worked_week_id = self.env['som.worked.week'].search([
                    ('som_employee_id', '=', employee_id.id),
                    ('som_week_id', '=', id_week),
                ])
                if not worked_week_id:
                    worked_week_id = self.env['som.worked.week'].create({
                        'som_employee_id': employee_id.id,
                        'som_week_id': id_week,
                    })

                timesheet_id = self.env['account.analytic.line'].search([
                    ('employee_id', '=', employee_id.id),
                    ('som_week_id', '=', id_week),
                    ('project_id', '=', project_ch_id.id),
                ])
                if timesheet_id:
                    timesheet_id.unit_amount = worked_hours
                else:
                    timesheet_id = self.env['account.analytic.line'].create({
                        'date': week_date,
                        'som_worked_week_id': worked_week_id.id,
                        'som_week_id': id_week,
                        'som_is_cumulative': True,
                        'employee_id': employee_id.id,
                        'project_id': project_ch_id.id,
                        'name': week_name,
                        'unit_amount': worked_hours,
                    })
            pass
