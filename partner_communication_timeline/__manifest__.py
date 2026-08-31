# -*- coding: utf-8 -*-

{
    "name": "Partner Communication Timeline",
    "summary": "Customer 360 communication timeline on contacts",
    "version": "16.0.1.2.0",
    "category": "Productivity",
    "author": "Som Energia",
    "website": "https://www.somenergia.coop",
    "license": "LGPL-3",
    "depends": ["base", "mail", "contacts", "crm", "helpdesk_mgmt", "base_search_mail_content"],
    "data": [
        "security/ir.model.access.csv",
        "views/mail_message_views.xml",
        "views/partner_communication_model_rule_views.xml",
        "views/res_partner_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
