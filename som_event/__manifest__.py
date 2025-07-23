# -*- coding: utf-8 -*-
{
    'name': "som_event",

    'summary': """
        Event customs for Som Energia
    """,

    'description': """
        Event customs for Som Energia
    """,

    'author': "Pere Montagud Ferragud ",
    'website': "https://github.com/Som-Energia/somenergia-odoo",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'event',
    ],

    # always loaded
    'data': [
        'data/event_data.xml',
        'security/event_security.xml',
        'views/event_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    # only loaded in demonstration mode
    'demo': [
    ],
}
