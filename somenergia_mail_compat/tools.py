from odoo import tools
from odoo.tools import mail


def _email_split_and_format_normalize(text):
    """Backport OCB 16 commit 2baa481e14ca705f4c6d3d4d900daf24442a4aa5."""
    return [
        tools.formataddr((name, tools.email_normalize(email)))
        for name, email in tools.email_split_tuples(text)
    ]


def _email_anonymize(normalized_email, *, redact_domain=False):
    """Backport OCB 16 commit c993ec371e966e84b12d5767e81a71228075a656."""
    if not normalized_email:
        return normalized_email

    local, at, domain = normalized_email.partition("@")
    if len(local) <= 5:
        anonymized_local = local[:1] + "*" * (len(local) - 1)
    else:
        anonymized_local = local[:1] + "*" * (len(local) - 3) + local[-2:]

    host, dot, tld = domain.rpartition(".")
    if redact_domain and not domain.startswith("[") and all((host, dot, tld)):
        anonymized_host = host[0] + "*" * (len(host) - 1)
    else:
        anonymized_host = host

    return f"{anonymized_local}{at}{anonymized_host}{dot}{tld}"


if not hasattr(tools, "email_split_and_format_normalize"):
    tools.email_split_and_format_normalize = _email_split_and_format_normalize

if not hasattr(mail, "email_anonymize"):
    mail.email_anonymize = _email_anonymize
