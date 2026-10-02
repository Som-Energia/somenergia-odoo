# -*- coding: utf-8 -*-
# notifica - Global configuration constants
#
# Central place for enum choices, defaults, and other shared configuration
# used across models, controllers, and hooks.

ORIGIN_APP_CHOICES = [
    ('odoo', 'Odoo'),
    ('mailchimp', 'Mailchimp'),
    ('ov', 'OV'),
]

ORIGIN_APP_DEFAULT = 'odoo'

# Set of valid origin_app keys (derived) — useful for sanitization
ORIGIN_APP_KEYS = {key for key, _label in ORIGIN_APP_CHOICES}

# Supported API request languages (company standard)
# ISO locale codes used by Odoo's res.lang
SUPPORTED_LANGS = [
    'es_ES',   # Spanish
    'ca_ES',   # Catalan
    'gl_ES',   # Galician
    'eu_ES',   # Basque
]
SUPPORTED_LANG_KEYS = set(SUPPORTED_LANGS)
SUPPORTED_LANG_DEFAULT = 'es_ES'
