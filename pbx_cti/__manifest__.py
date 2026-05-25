# Copyright 2024 Som Energia SCCL
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "PBX CTI — Incoming Call Popup",
    "version": "16.0.1.0.0",
    "category": "Phone",
    "summary": "Receives Irontec PBX webhook and opens the caller's partner form",
    "author": "Som Energia SCCL",
    "website": "https://www.somenergia.coop",
    "license": "AGPL-3",
    "depends": ["base", "bus"],
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
