from odoo import fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = ['hr.employee.base']

    department_ids = fields.Many2many(
        'hr.department', 'employee_department_rel',
        'employee_id', 'department_id',
        string='Departments')


class Employee(models.Model):
    _inherit = ['hr.employee']


class Department(models.Model):
    _inherit = ['hr.department']

    members_ids = fields.Many2many(
        'hr.employee', 'employee_department_rel',
        'department_id', 'employee_id',
        string='Members')
