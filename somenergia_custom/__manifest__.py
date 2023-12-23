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
    ],

    # always loaded
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/hr_attendance_view.xml',
        'views/hr_leave_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
