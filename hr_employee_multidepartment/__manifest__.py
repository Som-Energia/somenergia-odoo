{
    'name': "HR Employee Multidepartment",
    'version': '16.0.0.0.0',
    'depends': [
        'hr',
        'hr_holidays',
    ],
    'author': """Som Energia SCCL,
    Odoo Community Association (OCA)
    """,
    'website': 'https://github.com/OCA/hr',
    'category': 'Human Resources',
    'summary': """
    Add multidepartment feature.
    """,
    'license': 'AGPL-3',
    'demo': [
    ],
    'data': [
        'views/hr_employee_views.xml',
        'views/hr_leave_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
