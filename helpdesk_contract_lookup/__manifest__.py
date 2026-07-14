{
    "name": "Helpdesk Contract Lookup",
    "summary": "Ad-hoc contract lookup for helpdesk users",
    "description": "Helpdesk contract lookup screen with real-time ERP queries.",
    "author": "Som Energia",
    "website": "https://www.somenergia.coop/",
    "category": "Services/Helpdesk",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "depends": [
        "base",
        "web",
        "helpdesk_mgmt",
        "odoo_callinfo",
    ],
    "data": [
        "security/lookup_security.xml",
        "views/crm_phonecall_views.xml",
        "views/menu.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "/helpdesk_contract_lookup/static/src/**/*.esm.js",
            "/helpdesk_contract_lookup/static/src/**/*.scss",
            "/helpdesk_contract_lookup/static/src/**/*.xml",
        ],
    },
    "installable": True,
}
