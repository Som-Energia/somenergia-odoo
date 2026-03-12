try:
    from odoo.addons.iap.tools.iap_tools import _MAIL_DOMAIN_BLACKLIST
    if isinstance(_MAIL_DOMAIN_BLACKLIST, set):
        _SOM_BLACKLISTED_DOMAINS = {
            'telefonica.net',
            'liquidrockentertainment.com',
            'coac.cat',
            'xtec.cat',
        }
        _MAIL_DOMAIN_BLACKLIST.update(_SOM_BLACKLISTED_DOMAINS)

except ImportError:
    pass
