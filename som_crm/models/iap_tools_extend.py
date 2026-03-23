try:
    from odoo.addons.iap.tools.iap_tools import _MAIL_DOMAIN_BLACKLIST
    if isinstance(_MAIL_DOMAIN_BLACKLIST, set):
        _SOM_BLACKLISTED_DOMAINS = {
            'telefonica.net',
            'liquidrockentertainment.com',
            'coac.cat',
            'xtec.cat',
            'movistar.es',
            'uoc.edu',
        }
        _MAIL_DOMAIN_BLACKLIST.update(_SOM_BLACKLISTED_DOMAINS)

except ImportError:
    pass
