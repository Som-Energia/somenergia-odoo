{
    "name": "PBX CTI — Incoming Call Popup",
    "version": "16.0.1.0.0",
    "category": "Phone",
    "summary": "Receives Irontec PBX webhook and opens the caller's partner form",
    "author": "Som Energia SCCL",
    "website": "https://www.somenergia.coop",
    "license": "AGPL-3",
    "depends": ["base", "bus", "helpdesk_contract_lookup", "odoo_callinfo"],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pbx_cti/static/src/pbx_cti_service.js",
        ],
    },
    "installable": True,
    "application": False,
}
