{
    "name": "Som WhatsApp",
    "summary": "Partner WhatsApp conversations",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Som Energia",
    "website": "https://github.com/Som-Energia/somenergia-odoo",
    "category": "Discuss",
    "depends": ["crm", "mail_gateway_whatsapp"],
    "data": [
        "views/crm_lead_views.xml",
        "views/res_partner_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "som_whatsapp/static/src/discuss/whatsapp_discuss_container.js",
        ],
    },
    "installable": True,
}
