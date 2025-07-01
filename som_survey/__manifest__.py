# -*- coding: utf-8 -*-
{
    'name': "som_survey",

    'summary': """
        Survey customs for Som Energia
    """,

    'description': """
        Survey customs for Som Energia
    """,

    'author': "Pere Montagud Ferragud ",
    'website': "https://www.somenergia.coop/",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'survey',
    ],

    # always loaded
    'data': [
        'views/survey_templates_management.xml',
        'views/survey_user_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
