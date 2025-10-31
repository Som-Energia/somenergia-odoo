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
        'utm',
        'crm',
        'product',
        'crm_lead_vat',
        'mail_activity_board',
        'odoo_callinfo',
    ],
    "external_dependencies": {"python": ["erppeek"]},

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/crm_stage_data.xml',
        'data/mail_template_data.xml',
        'views/crm_lead_views.xml',
        'views/contact_time_slot_views.xml',
        'views/res_users_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/crm_lead_lost_views.xml',
        'views/mail_activity_views.xml',
        'views/phone_call_result_views.xml',
        'views/crm_phonecall_views.xml',
        'views/utm_menus.xml',
        'views/crm_stage_views.xml',
        'views/mail_message.xml',
        'report/crm_pivot_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    # only loaded in demonstration mode
    'demo': [
    ],
}
