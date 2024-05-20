# -*- coding: utf-8 -*-
{
    'name': "somenergia_custom",

    'summary': """
        Custom features""",

    'description': """
        Custom features
    """,

    'author': "Pere Montagud Ferragud ",
    'website': "https://www.somenergia.coop/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'hr_attendance_report_theoretical_time',
        'hr_holidays',
        'hr_holidays_attendance',
        'project',
        'analytic',
        'hr_timesheet',
        'hr_attendance_autoclose',
        'hr_employee_multidepartment',
        'hr_employee_calendar_planning',
        'custom_pnt',
    ],

    # always loaded
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'security/som_worked_week_security.xml',
        'security/hr_attendance_report_security.xml',
        'security/hr_attendance_overtime_security.xml',
        'security/project_security.xml',
        'views/hr_attendance_view.xml',
        'views/hr_leave_view.xml',
        'views/som_calendar_week_view.xml',
        'views/hr_timesheet_view.xml',
        'views/som_worked_week_view.xml',
        'views/hr_employee_view.xml',
        'views/hr_attendance_overtime_view.xml',
        'views/project_view.xml',
        'views/project_task_view.xml',
        'views/hr_contract_view.xml',
        'wizards/hr_contract_import_wizard.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
