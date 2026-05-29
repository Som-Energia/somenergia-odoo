{
    'name': "notifica",

    'summary': """
        Unified communication log for tracking internal and external
        communications across all contact points.
    """,

    'description': """
        Centralises communications from Odoo chatter and external API calls
        into a dedicated comm.log model. Supports configurable capture rules,
        bidirectional partner scope (parent-child contacts), and secure
        API token authentication with Pydantic validation.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Sales',
    'version': '16.0.0.2',

    'depends': ['base', 'mail', 'contacts'],

    'data': [
        'security/ir.model.access.csv',
        'views/partner_views.xml',
        'views/comm_log_views.xml',
        'views/comm_log_rule_views.xml',
    ],
}
