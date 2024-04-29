# -*- coding: utf-8 -*-
{
    'name': "odoo_callinfo",

    'summary': """
        Integration Odoo and Tomàtic / CallInfo""",

    'description': """
        Integration Odoo and Tomàtic / CallInfo
    """,

    'author': "Pere Montagud Ferragud ",
    'website': "https://www.somenergia.coop/",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'crm',
        'crm_phonecall',
    ],

    # always loaded
    'data': [
        'data/data.xml',
        'views/crm_phonecall_view.xml',
        'views/product_category.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
