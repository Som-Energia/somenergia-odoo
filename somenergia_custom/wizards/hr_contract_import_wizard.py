# -*- coding: utf-8 -*-
import base64
import xlrd
import time
import calendar
import datetime
from odoo import api, fields, models, exceptions, _
from xlrd import open_workbook
from datetime import datetime
import datetime as dt
from datetime import datetime, timedelta
from odoo.tests import common, Form
import logging
_logger = logging.getLogger(__name__)


class HrContractImportWizard(models.TransientModel):
    _name = 'hr.contract.import.wizard'

    som_xls = fields.Binary(
        string='Excel document',
        required=True,
    )

    @api.model
    def default_get(self, fields):
        record_ids = self._context.get('active_ids')
        result = super(HrContractImportWizard, self).default_get(fields)
        return result

    def _create_contract(self, employee_id, start_date, end_date,
                         grade_id, rank_id, complement_id,
                         contract_number):
        hr_responsible_id = self.env['res.users'].browse(258)
        hr_contract_form = Form(self.env['hr.contract'])
        hr_contract_form.employee_id = employee_id
        hr_contract_form.name = "#%s %s" % (str(contract_number), employee_id.name)
        hr_contract_form.date_start = start_date
        hr_contract_form.date_end = end_date
        hr_contract_form.hr_responsible_id = hr_responsible_id
        if grade_id:
            hr_contract_form.pnt_grade_id = grade_id
        if rank_id:
            hr_contract_form.pnt_rank_id = rank_id
        if complement_id:
            hr_contract_form.pnt_salary_complement_id = complement_id
        hr_contract_id = hr_contract_form.save()
        self.env['hr.contract'].update_state()
        self.env['hr.contract'].update_state()
        return hr_contract_id

    def _get_grade_rank_complement(self, str_rank):
        list_aux = str_rank.split('+')
        rank = list_aux[0]
        grade = rank[:-1] if len(rank) > 1 else rank
        grade_id = self.env['grade.grade'].search([('name', '=', grade)])[0]
        rank_id = self.env['rank.rank'].search([('name', '=', rank)])[0]
        complement_id = False
        if len(list_aux) ==2:
            complement = list_aux[1]
            complement_id = self.env['rank.rank'].search([('name', '=', complement)])[0]
        return grade_id, rank_id, complement_id

    def do_import(self):
        xls = open_workbook(file_contents=base64.decodestring(self.som_xls))
        sheets = xls.sheets()
        sheet = sheets[0]
        init_data_row = 1
        limit_columns = 15

        for row in range(sheet.nrows):
            if row < init_data_row:
                continue
            name = sheet.cell(row, 0).value
            email = sheet.cell(row, 1).value
            start_date = (dt.datetime(1899, 12, 30) +
                          dt.timedelta(days=sheet.cell(row, 2).value))

            user_id = self.env['res.users'].search([
                ('login', '=', email)
            ])
            if not user_id:
                _logger.info('% not found', email)
                continue
            employee_id = user_id.employee_id
            employee_id.som_recruitment_date = start_date
            i = 3
            count_contracts_employee = 0
            while i < limit_columns:
                col_aux = i
                year = sheet.cell(0, col_aux).value
                rank_current = sheet.cell(row, col_aux).value

                if not rank_current:
                    i += 1
                    continue

                contract_start_date = dt.datetime(
                    int(year), start_date.month, start_date.day
                )

                # start date before first contract in 2020
                if count_contracts_employee == 0 and start_date < contract_start_date:
                    contract_id = self._create_contract(
                        employee_id,
                        start_date,
                        (contract_start_date - timedelta(days=1)),
                        False, False, False,
                        count_contracts_employee,
                    )

                # get next change if exits
                rank_next_year = ''
                flag_create_contract = False
                contract_end_date = False
                j = i
                while j <= limit_columns and not flag_create_contract:
                    j += 1
                    rank_next_year = sheet.cell(row, j).value
                    flag_create_contract = (
                        (rank_next_year and rank_current != rank_next_year) or (j == limit_columns)
                    )
                if flag_create_contract:
                    i = j
                    if rank_next_year:
                        year_next = sheet.cell(0, i).value
                        contract_end_date = (
                            dt.datetime(int(year_next), start_date.month, start_date.day) - timedelta(days=1)
                        )

                    # get grade, rank and complement
                    grade_id, rank_id, complement_id = self._get_grade_rank_complement(rank_current)

                    # create contract
                    _logger.info("EMPLOYEE %s - START: %s - END: %s - RANK %s",
                                 str(email), str(contract_start_date), str(contract_end_date), rank_current)
                    count_contracts_employee += 1
                    contract_id = self._create_contract(
                        employee_id,
                        contract_start_date,
                        contract_end_date,
                        grade_id, rank_id, complement_id,
                        count_contracts_employee,
                    )
