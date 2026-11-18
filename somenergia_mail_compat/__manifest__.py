{
    "name": "SomEnergia Mail Compatibility",
    "version": "16.0.1.1.0",
    "summary": "Mail API compatibility for the pinned OCB 16 core",
    "category": "Technical",
    "author": "Som Energia SCCL",
    "website": "https://www.somenergia.coop/",
    "license": "AGPL-3",
    "depends": ["mail"],
    "assets": {
        "web.assets_backend": [
            "somenergia_mail_compat/static/src/models/message.js",
        ],
        "web.qunit_suite_tests": [
            "somenergia_mail_compat/static/tests/message_tests.js",
        ],
    },
    "installable": True,
    "application": False,
}
