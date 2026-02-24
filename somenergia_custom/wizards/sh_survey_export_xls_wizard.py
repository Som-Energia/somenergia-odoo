# -*- coding: utf-8 -*-
from odoo import fields, models
import xlwt
from odoo.exceptions import UserError
import base64
import io


class SurveyExportWizard(models.TransientModel):
    _inherit = "sh.survey.export.wizard"

    def get_default_hr_appraisal_id(self):
        if self.env.context.get('active_model') == 'hr.appraisal':
            return self.env.context.get('active_id')
        return False

    def get_default_survey_domain_ids(self):
        if self.env.context.get('active_model') == 'hr.appraisal':
            appraisal_id = self.env['hr.appraisal'].browse(self.env.context.get('active_id'))
            ids_appr_survey = []
            if appraisal_id.emp_survey_id:
                ids_appr_survey.append(appraisal_id.emp_survey_id.id)
            if appraisal_id.colleague_survey_id:
                ids_appr_survey.append(appraisal_id.colleague_survey_id.id)
            if appraisal_id.collaborator_survey_id:
                ids_appr_survey.append(appraisal_id.collaborator_survey_id.id)
            return ids_appr_survey
        else:
            # active_model is survey.survey, so we return the active_id in a list
            return [self.env.context.get('active_id')]

    def get_default_survey(self):
        if self.env.context.get('active_model') == 'hr.appraisal':
            return False
        else:
            # active_model is survey.survey, so we return the active_id
            return self.env.context.get('active_id')

    som_hr_appraisal_id = fields.Many2one(
        comodel_name="hr.appraisal",
        string="Feedback",
        default=get_default_hr_appraisal_id,
        required=True,
    )

    som_survey_id = fields.Many2one(
        comodel_name="survey.survey",
        string="Survey",
        required=True,
        default=get_default_survey,
    )

    som_survey_domain_ids = fields.Many2many(
        comodel_name="survey.survey",
        string="Survey domain",
        default=get_default_survey_domain_ids,
        store=False,
        readonly=False,
    )

    def _get_domain(self, active_id):
        domain = [('survey_id', '=', active_id.id)]
        if self.sh_complete_survery:
            domain.append(('state', '=', 'done'))
        if self.som_hr_appraisal_id:
            domain.append(('appraisal_id', '=', self.som_hr_appraisal_id.id))
        return domain

    def get_xls_report(self):
        if self:
            active_id = self.som_survey_id
            domain = self._get_domain(active_id)
            user_inputs = self.env['survey.user_input'].sudo().search(domain)

            column_width_list = []
            question_list = []
            options_dic = {}
            row_dic = {}
            row_option_dic = {}
            question_ids = self.env['survey.question'].sudo().search(
                [('survey_id', '=', active_id.id), ('is_page', '=', False)])
            question_list.append('Person')
            column_width_list.append(len('Person')+5)
            for question in question_ids:
                if question.question_type in ['text_box', 'char_box', 'numerical_box', 'date', 'datetime', 'simple_choice']:
                    question_list.append(question.title)
                    column_width_list.append(len(question.title)+2)
                elif question.question_type in ['multiple_choice']:
                    options_dic[question.title] = []
                    for suggest in question.suggested_answer_ids:
                        column_width_list.append(len(question.title))
                        question_list.append(question.title)
                        options_dic[question.title].append(suggest.value)
                elif question.question_type in ['matrix']:
                    row_dic[question.title] = []
                    row_option_dic[question.title] = []
                    for row in question.matrix_row_ids:
                        question_list.append(question.title)
                        row_dic[question.title].append(row.value)
                        if len(question.title) > len(row.value):
                            column_width_list.append(len(question.title)+5)
                        else:
                            column_width_list.append(len(row.value))
            boolean = False
            survey_dic = {}
            unknown_partner=0
            for user in user_inputs:
                boolean = False
    
                if type(user.partner_id.name) != bool:
                    if column_width_list[0] < (len(user.partner_id.name)):
                        column_width_list[0] = len(user.partner_id.name)
                    survey_dic[user.partner_id.name] = []
                    if self.sh_group_by_partner:
                        for i in range(0, len(question_list)):
                            survey_dic[user.partner_id.name].append('')
                    else:
                        for i in range(0, len(question_list)-1):
                            survey_dic[user.partner_id.name].append('')
                    for line in user.user_input_line_ids:
                        if line.question_id.title in question_list:
                            answer_id = self.env['survey.user_input.line'].sudo().search(
                                [('question_id', '=', line.question_id.id), ('survey_id', '=', active_id.id), ('user_input_id', '=', user.id)])
                            if line.question_id.question_type == 'text_box':
                                if boolean:
                                    survey_dic[user.partner_id.name][question_list.index(
                                        line.question_id.title)] = answer_id.value_text_box
                                    if type(answer_id.value_text_box) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)] < (len(str(answer_id.value_text_box))):
                                            column_width_list[question_list.index(
                                                line.question_id.title)] = len(str(answer_id.value_text_box))
                                else:
                                    survey_dic[user.partner_id.name][question_list.index(
                                        line.question_id.title)-1] = answer_id.value_text_box
                                    if type(answer_id.value_text_box) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)-1] < (len(str(answer_id.value_text_box))):
                                            column_width_list[question_list.index(
                                                line.question_id.title)-1] = len(str(answer_id.value_text_box))
                            if line.question_id.question_type == 'char_box':
                                if boolean:
                                    survey_dic[user.partner_id.name][question_list.index(
                                        line.question_id.title)] = answer_id.value_char_box
                                    if type(answer_id.value_char_box) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)] < (len(answer_id.value_char_box)):
                                            column_width_list[question_list.index(
                                                line.question_id.title)] = len(answer_id.value_char_box)
                                else:
                                    survey_dic[user.partner_id.name][question_list.index(
                                        line.question_id.title)-1] = answer_id.value_char_box
                                    if type(answer_id.value_char_box) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)-1] < (len(answer_id.value_char_box)):
                                            column_width_list[question_list.index(
                                                line.question_id.title)-1] = len(answer_id.value_char_box)
                            if line.question_id.question_type == 'numerical_box':
                                if boolean:
                                    survey_dic[user.partner_id.name][question_list.index(
                                        line.question_id.title)] = answer_id.value_numerical_box
                                else:
                                    survey_dic[user.partner_id.name][question_list.index(
                                        line.question_id.title)-1] = answer_id.value_numerical_box
                            if line.question_id.question_type == 'date':
                                if boolean:
                                    survey_dic[user.partner_id.name][question_list.index(
                                        line.question_id.title)] = str(answer_id.value_date)
                                    if type(answer_id.value_date) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)] < (len(str(answer_id.value_date))):
                                            column_width_list[question_list.index(
                                                line.question_id.title)] = len(str(answer_id.value_date))
                                else:
                                    survey_dic[user.partner_id.name][question_list.index(
                                        line.question_id.title)-1] = str(answer_id.value_date)
                                    if type(answer_id.value_date) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)-1] < (len(str(answer_id.value_date))):
                                            column_width_list[question_list.index(
                                                line.question_id.title)-1] = len(str(answer_id.value_date))
                            if line.question_id.question_type == 'datetime':
                                if boolean:
                                    survey_dic[user.partner_id.name][question_list.index(
                                        line.question_id.title)] = str(answer_id.value_datetime)
                                    if type(answer_id.value_datetime) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)] < (len(str(answer_id.value_datetime))):
                                            column_width_list[question_list.index(
                                                line.question_id.title)] = len(str(answer_id.value_datetime))
                                else:
                                    survey_dic[user.partner_id.name][question_list.index(
                                        line.question_id.title)-1] = str(answer_id.value_datetime)
                                    if type(answer_id.value_datetime) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)-1] < (len(str(answer_id.value_datetime))):
                                            column_width_list[question_list.index(
                                                line.question_id.title)-1] = len(str(answer_id.value_datetime))
                            if line.question_id.question_type == 'simple_choice':
                                if boolean:
                                    survey_dic[user.partner_id.name][question_list.index(
                                        line.question_id.title)] = answer_id.suggested_answer_id.value
                                    if type(answer_id.suggested_answer_id.value) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)] < (len(answer_id.suggested_answer_id.value)):
                                            column_width_list[question_list.index(
                                                line.question_id.title)] = len(answer_id.suggested_answer_id.value)
                                else:
                                    survey_dic[user.partner_id.name][question_list.index(
                                        line.question_id.title)-1] = answer_id.suggested_answer_id.answer_score or answer_id.suggested_answer_id.value
                                    if type(answer_id.suggested_answer_id.value) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)-1] < (len(answer_id.suggested_answer_id.value)):
                                            column_width_list[question_list.index(
                                                line.question_id.title)-1] = len(answer_id.suggested_answer_id.value)
                            if line.question_id.question_type == 'multiple_choice':
                                for suggest in line.question_id.suggested_answer_ids:
                                    temp_list = []
                                    for option in answer_id.suggested_answer_id:
                                        temp_list.append(option.value)
                                    if boolean:
                                        if suggest.value in temp_list:
                                            index = options_dic[line.question_id.title].index(
                                                suggest.value)
                                            survey_dic[user.partner_id.name][question_list.index(
                                                line.question_id.title)+index] = suggest.value
                                        else:
                                            index = options_dic[line.question_id.title].index(
                                                suggest.value)
                                            survey_dic[user.partner_id.name][question_list.index(
                                                line.question_id.title)+index] = ''
                                    else:
                                        if suggest.value in temp_list:
                                            index = options_dic[line.question_id.title].index(
                                                suggest.value)
                                            survey_dic[user.partner_id.name][question_list.index(
                                                line.question_id.title)-1+index] = suggest.value
                                        else:
                                            index = options_dic[line.question_id.title].index(
                                                suggest.value)
                                            survey_dic[user.partner_id.name][question_list.index(
                                                line.question_id.title)-1+index] = ''
                            if line.question_id.question_type == 'matrix':
                                temp_row_dic = {}
                                for answer in answer_id:
                                    if answer.matrix_row_id.value:
                                        if answer.matrix_row_id.value not in temp_row_dic.keys():
                                            temp_row_dic[answer.matrix_row_id.value] = ''

                                        # update changes
                                        if answer.suggested_answer_id.value:
                                            temp_row_dic[answer.matrix_row_id.value] += answer.suggested_answer_id.value
                                            temp_row_dic[answer.matrix_row_id.value] += ','      

                                        else:
                                            temp_row_dic[answer.matrix_row_id.value] += ' '

                                        # temp_row_dic[answer.matrix_row_id.value] += answer.suggested_answer_id.value
                                        # temp_row_dic[answer.matrix_row_id.value] += ','      

                                for row in range(0, len(row_dic[line.question_id.title])):
                                    if row == 0 and not boolean and self.sh_group_by_partner:
                                        survey_dic[user.partner_id.name][question_list.index(
                                            line.question_id.title)-1] = ''
                                        boolean = True
                                    if boolean:
                                        survey_dic[user.partner_id.name][question_list.index(
                                            line.question_id.title)+row] = temp_row_dic[row_dic[line.question_id.title][row]] if row_dic[line.question_id.title][row] in temp_row_dic.keys() else ' '
                                    else:
                                        survey_dic[user.partner_id.name][question_list.index(line.question_id.title)-1+row] = temp_row_dic[row_dic[line.question_id.title][row]] if row_dic[line.question_id.title][row] in temp_row_dic.keys() else ' '

                else:
                    unknown_partner+=1
                    survey_dic['Unknown'+ str(unknown_partner)] = []

                    if self.sh_group_by_partner:
                        for i in range(0, len(question_list)):
                            survey_dic['Unknown'+ str(unknown_partner)].append('')
                    else:
                        for i in range(0, len(question_list)-1):
                            survey_dic['Unknown'+ str(unknown_partner)].append('')
                    for line in user.user_input_line_ids:
                        if line.question_id.title in question_list:
                            answer_id = self.env['survey.user_input.line'].sudo().search(
                                [('question_id', '=', line.question_id.id), ('survey_id', '=', active_id.id), ('user_input_id', '=', user.id)])
                            if line.question_id.question_type == 'text_box':
                                if boolean:
                                    survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                        line.question_id.title)] = answer_id.value_text_box
                                    if type(answer_id.value_text_box) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)] < (len(str(answer_id.value_text_box))):
                                            column_width_list[question_list.index(
                                                line.question_id.title)] = len(str(answer_id.value_text_box))
                                else:
                                    survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                        line.question_id.title)-1] = answer_id.value_text_box
                                    if type(answer_id.value_text_box) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)-1] < (len(str(answer_id.value_text_box))):
                                            column_width_list[question_list.index(
                                                line.question_id.title)-1] = len(str(answer_id.value_text_box))
                            if line.question_id.question_type == 'char_box':
                                if boolean :
                                    survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                        line.question_id.title)] = answer_id.value_char_box
                                    if type(answer_id.value_char_box) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)] < (len(answer_id.value_char_box)):
                                            column_width_list[question_list.index(
                                                line.question_id.title)] = len(answer_id.value_char_box)
                                else:
                                    survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                        line.question_id.title)-1] = answer_id.value_char_box
                                    if type(answer_id.value_char_box) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)-1] < (len(answer_id.value_char_box)):
                                            column_width_list[question_list.index(
                                                line.question_id.title)-1] = len(answer_id.value_char_box)
                            if line.question_id.question_type == 'numerical_box':
                                if boolean:
                                    survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                        line.question_id.title)] = answer_id.value_numerical_box
                                else:
                                    survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                        line.question_id.title)-1] = answer_id.value_numerical_box
                            if line.question_id.question_type == 'date':
                                if boolean:
                                    survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                        line.question_id.title)] = str(answer_id.value_date)
                                    if type(answer_id.value_date) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)] < (len(str(answer_id.value_date))):
                                            column_width_list[question_list.index(
                                                line.question_id.title)] = len(str(answer_id.value_date))
                                else:
                                    survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                        line.question_id.title)-1] = str(answer_id.value_date)
                                    if type(answer_id.value_date) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)-1] < (len(str(answer_id.value_date))):
                                            column_width_list[question_list.index(
                                                line.question_id.title)-1] = len(str(answer_id.value_date))
                            if line.question_id.question_type == 'datetime':
                                if boolean :
                                    survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                        line.question_id.title)] = str(answer_id.value_datetime)
                                    if type(answer_id.value_datetime) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)] < (len(str(answer_id.value_datetime))):
                                            column_width_list[question_list.index(
                                                line.question_id.title)] = len(str(answer_id.value_datetime))
                                else:
                                    survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                        line.question_id.title)-1] = str(answer_id.value_datetime)
                                    if type(answer_id.value_datetime) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)-1] < (len(str(answer_id.value_datetime))):
                                            column_width_list[question_list.index(
                                                line.question_id.title)-1] = len(str(answer_id.value_datetime))
                            if line.question_id.question_type == 'simple_choice':
                                if boolean:
                                    survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                        line.question_id.title)] = answer_id.suggested_answer_id.value
                                    if type(answer_id.suggested_answer_id.value) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)] < (len(answer_id.suggested_answer_id.value)):
                                            column_width_list[question_list.index(
                                                line.question_id.title)] = len(answer_id.suggested_answer_id.value)
                                else:
                                    survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                        line.question_id.title)-1] = answer_id.suggested_answer_id.value
                                    if type(answer_id.suggested_answer_id.value) != bool:
                                        if column_width_list[question_list.index(line.question_id.title)-1] < (len(answer_id.suggested_answer_id.value)):
                                            column_width_list[question_list.index(
                                                line.question_id.title)-1] = len(answer_id.suggested_answer_id.value)
                            if line.question_id.question_type == 'multiple_choice':
                                for suggest in line.question_id.suggested_answer_ids:
                                    temp_list = []
                                    for option in answer_id.suggested_answer_id:
                                        temp_list.append(option.value)
                                    if boolean :
                                        if suggest.value in temp_list:
                                            index = options_dic[line.question_id.title].index(
                                                suggest.value)
                                            survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                                line.question_id.title)+index] = suggest.value
                                        else:
                                            index = options_dic[line.question_id.title].index(
                                                suggest.value)
                                            survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                                line.question_id.title)+index] = ''
                                    else:
                                        if suggest.value in temp_list:
                                            index = options_dic[line.question_id.title].index(
                                                suggest.value)
                                            survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                                line.question_id.title)-1+index] = suggest.value
                                        else:
                                            index = options_dic[line.question_id.title].index(
                                                suggest.value)
                                            survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                                line.question_id.title)-1+index] = ''
                            if line.question_id.question_type == 'matrix':
                                temp_row_dic = {}

                                for answer in answer_id:
                                    if answer.matrix_row_id.value:
                                        if answer.matrix_row_id.value not in temp_row_dic.keys():
                                            temp_row_dic[answer.matrix_row_id.value] = ''
                                            
                                        if answer.suggested_answer_id.value:
                                            temp_row_dic[answer.matrix_row_id.value] += answer.suggested_answer_id.value
                                            temp_row_dic[answer.matrix_row_id.value] += ','

                                        else:
                                            temp_row_dic[answer.matrix_row_id.value] +=' '

                                        # temp_row_dic[answer.matrix_row_id.value] += answer.suggested_answer_id.value
                                        # temp_row_dic[answer.matrix_row_id.value] += ','

                                for row in range(0, len(row_dic[line.question_id.title])):
                                    if row == 0 and not boolean and self.sh_group_by_partner:
                                        survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                            line.question_id.title)-1] = ''
                                        boolean = True
                                    if boolean:
                                        survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                            line.question_id.title)+row] = temp_row_dic[row_dic[line.question_id.title][row]] if row_dic[line.question_id.title][row] in temp_row_dic.keys() else ' '
                                    else:
                                        survey_dic['Unknown'+ str(unknown_partner)][question_list.index(
                                            line.question_id.title)-1+row] = temp_row_dic[row_dic[line.question_id.title][row]] if row_dic[line.question_id.title][row] in temp_row_dic.keys() else ' '
        workbook = xlwt.Workbook()
        bold_center = xlwt.easyxf(
            'font:height 250,bold True;align: vert center')
        normal_record = xlwt.easyxf('font:height 210;align: vert center')
        heading_format = xlwt.easyxf(
            'font:height 245,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        worksheet = workbook.add_sheet("Survery Answers Report", bold_center)
        line_var = 1

        worksheet.write_merge(line_var, line_var, 2, 3,
                              'Survery Answers Report', heading_format)
        line_var += 2
        worksheet.write_merge(
            line_var, line_var, 2, 3, 'Today Date : ' + str(fields.Date.today()), heading_format)

        if self.sh_group_by_partner:

            worksheet.col(0).width = 1000
            worksheet.col(1).width = 13000
            worksheet.col(2).width = 13000
            worksheet.col(3).width = 7000
            worksheet.col(4).width = 7000
            if question_list:
                if survey_dic:
                    partner_list = list(survey_dic.keys())
                    for partner in range(0, len(partner_list)):
                        counter3 = 0
                        worksheet.write_merge(
                            line_var, line_var, 2, 3, partner_list[partner], heading_format)
                        line_var += 2
                        temp_line = line_var
                        count = 0
                        for question in range(1, len(question_list)):
                            count += 1
                            worksheet.write_merge(
                                line_var, line_var, 0, 0, count, normal_record)
                            if question_list[question-1] and question_list[question] != question_list[question-1]:
                                worksheet.write_merge(
                                    line_var, line_var, 1, 2, question_list[question], normal_record)
                                temp_l = line_var
                                line_var += 1
                            elif question_list[question] in options_dic.keys():
                                worksheet.write_merge(
                                    line_var, line_var, 1, 2, question_list[question], normal_record)
                                line_var += 1
                            if question_list[question] in row_dic.keys():
                                temp_row_list = row_dic[question_list[question]]
                                if counter3 < len(temp_row_list):
                                    if temp_l+1 == line_var:
                                        count += 1
                                        worksheet.write_merge(
                                            line_var, line_var, 0, 0, count, normal_record)
                                    else:
                                        worksheet.write_merge(
                                            line_var, line_var, 0, 0, count, normal_record)
                                    worksheet.write_merge(
                                        line_var, line_var, 1, 2, temp_row_list[counter3], normal_record)
                                    counter3 += 1
                                    line_var += 1

                        # if question+1 < len(question_list) and question_list[question] != question_list[question+1]:
                        #     counter3 = 0

                        for survery in survey_dic[partner_list[partner]]:
                            worksheet.write_merge(
                                temp_line, temp_line, 3, 4, survery, normal_record)

                            temp_line += 1
                        line_var += 2

        else:
            for i in range(0, len(column_width_list)):
                if column_width_list[i]*300 < 65536:
                    worksheet.col(i).width = column_width_list[i]*300
                else:
                    worksheet.col(i).width = 65535


            line_var += 2
            if question_list:
                col_var = 0
                counter1 = 0
                counter2 = 0
                length = len(question_list)
                for question in range(0, len(question_list)):
                    worksheet.write_merge(
                        line_var, line_var, col_var, col_var, question_list[question], heading_format)

                    if question_list[question] in options_dic.keys():
                        worksheet.write_merge(line_var+1, line_var+1, col_var, col_var,
                                              options_dic[question_list[question]][counter1], heading_format)
                        counter1 += 1
                    if question_list[question] in row_dic.keys():

                        # update code here by add if condition only
                        # =========================================
                        if counter2 < len(row_dic[question_list[question]]):
                            worksheet.write_merge(line_var+1, line_var+1, col_var, col_var,
                                            row_dic[question_list[question]][counter2], heading_format)
                            counter2 += 1
                    col_var += 1

                    if length != col_var and question_list[question] != question_list[question+1]:
                        counter1 = 0
                        counter2 = 0
            line_var += 1

            line_var += 1

            if survey_dic:
                partner_list = list(survey_dic.keys())
                for partner in range(0, len(partner_list)):
                    worksheet.write_merge(
                        line_var, line_var, 0, 0, partner_list[partner], normal_record)
                    col_var = 1
                    for survery in survey_dic[partner_list[partner]]:
                        worksheet.write_merge(
                            line_var, line_var, col_var, col_var, survery, normal_record)
                        col_var += 1
                    line_var += 1

        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env['ir.attachment']
        attachment_vals = {
            "name": "Survey Export.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search([('name', '=', 'survey_export'),
                                          ('type', '=', 'binary'),
                                          ('res_model', '=', 'ir.ui.view')],
                                         limit=1)
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = IrAttachment.create(attachment_vals)
        # TODO: make user error here
        if not attachment:
            raise UserError('There is no attachments...')

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

