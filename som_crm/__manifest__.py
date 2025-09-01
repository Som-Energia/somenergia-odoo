# -*- coding: utf-8 -*-
{
    'name': "som_crm",

    'summary': """
        CRM customs
    """,

    'description': """
        CRM customs
    """,

    'author': "Pau Boix i Tura, Pere Montagud Ferragud ",
    'website': "https://github.com/Som-Energia/somenergia-odoo",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'crm',
        'crm_lead_vat',
        'mail_activity_board',
        'odoo_callinfo',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/crm_lead_views.xml',
        'views/contact_time_slot_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
