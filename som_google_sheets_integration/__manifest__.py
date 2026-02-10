{
    'name': 'Som Google Sheets Integration',
    'version': '16.0.1.0.0',
    'category': 'Tools',
    'summary': 'It allows to connect to a Google Drive file',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/gsheets_view.xml',
    ],
    'installable': True,
    'application': True,
}
