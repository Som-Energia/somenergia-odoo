try:
    from odoo.addons.iap.tools.iap_tools import _MAIL_DOMAIN_BLACKLIST
    if isinstance(_MAIL_DOMAIN_BLACKLIST, set):
        _MAIL_DOMAIN_BLACKLIST.add('telefonica.net')

except ImportError:
    pass
