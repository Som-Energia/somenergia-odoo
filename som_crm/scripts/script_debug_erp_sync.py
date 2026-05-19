# -*- coding: utf-8 -*-
# Debug script for _erp_sync matching logic.
# Use from iPython to inspect why a lead is not matching in ERP.
#
# --- Mock mode (no ERP connection needed) ---
#
#   import importlib.util
#   spec = importlib.util.spec_from_file_location("debug", "/path/to/script_debug_erp_sync.py")
#   mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
#
#   lead_data = {
#       'som_cups': 'ES0031406533910001JN0F',
#       'vat': '12345678Z',
#       'email_from': 'test@example.com',
#       'phone': '+34 612 345 678',
#   }
#   erp_leads = [
#       {'id': 1, 'cups': 'ES0031406533910001JN', 'titular_vat': 'ES12345678Z',
#        'titular_email': '', 'titular_phone': '', 'crm_lead_id': 0},
#   ]
#   mod.debug_lead(lead_data, erp_leads)
#
# --- Real ERP mode (erppeek) ---
#
#   erp_conn = {
#       'server': 'http://erp.example.com:8069',
#       'db': 'my_db',
#       'user': 'admin',
#       'password': 'secret',
#   }
#   mod.debug_lead_erp(lead_data, erp_conn)

# ---------------------------------------------------------------------------
# Domain builders (mirror production logic exactly)
# ---------------------------------------------------------------------------

def _build_cups_domain(base_domain, cups_value):
    cups_truncated = cups_value[:20]
    return base_domain + [('cups', '=ilike', f'{cups_truncated}%')], cups_truncated


def _build_vat_domain(base_domain, vat_value):
    normalized = vat_value if vat_value.startswith('ES') else f'ES{vat_value}'
    return base_domain + [('titular_vat', '=', normalized)], normalized


def _build_email_domain(base_domain, email_value):
    email_upper = email_value.upper()
    return base_domain + ['|', ('titular_email', '=', email_value), ('titular_email', '=', email_upper)], email_upper


def _build_phone_domain(base_domain, phone_value):
    casted = phone_value
    if len(phone_value) > 9:
        casted = phone_value.replace(' ', '')[3:]
    return base_domain + [('titular_phone', '=', casted)], casted


STRATEGIES = [
    ('som_cups',   'CUPS',  _build_cups_domain),
    ('vat',        'VAT',   _build_vat_domain),
    ('email_from', 'EMAIL', _build_email_domain),
    ('phone',      'PHONE', _build_phone_domain),
]


# ---------------------------------------------------------------------------
# Mock ERP object
# ---------------------------------------------------------------------------

def _apply_domain(leads, domain):
    return [lead for lead in leads if _matches(lead, domain)]


def _matches(lead, domain):
    i = 0
    conditions = []
    while i < len(domain):
        item = domain[i]
        if item == '|':
            left = _eval_condition(lead, domain[i + 1])
            right = _eval_condition(lead, domain[i + 2])
            conditions.append(left or right)
            i += 3
        else:
            conditions.append(_eval_condition(lead, item))
            i += 1
    return all(conditions)


def _eval_condition(lead, condition):
    field, operator, value = condition
    lead_value = lead.get(field)
    if operator == '=':
        return lead_value == value
    elif operator == '=ilike':
        if value.endswith('%'):
            prefix = value[:-1].lower()
            return str(lead_value or '').lower().startswith(prefix)
        return str(lead_value or '').lower() == value.lower()
    else:
        raise NotImplementedError(f"Operator '{operator}' not implemented in mock")


class MockErpLeadObj:
    """Simulates erppeek's model object for giscedata.crm.lead."""

    def __init__(self, leads):
        self._leads = leads

    def search(self, domain, limit=None):
        results = _apply_domain(self._leads, domain)
        if limit:
            results = results[:limit]
        return [r['id'] for r in results]

    def read(self, ids, fields):
        return [
            {f: lead.get(f) for f in fields}
            for lead in self._leads
            if lead['id'] in ids
        ]


# ---------------------------------------------------------------------------
# Shared debug logic (works with both mock and real erp_lead_obj)
# ---------------------------------------------------------------------------

def _debug_with_obj(lead_data, erp_lead_obj, is_mock=False, mock_leads=None):
    base_domain = [('crm_lead_id', '=', 0)]

    print("=" * 60)
    print(f"ERP SYNC DEBUG ({'mock' if is_mock else 'real ERP'})")
    print("=" * 60)

    for lead_field, label, build_domain_fn in STRATEGIES:
        value = lead_data.get(lead_field)
        print(f"\n[{label}]")

        if not value:
            print(f"  valor: (buit) → estratègia saltada")
            continue

        print(f"  valor original   : {value!r}")
        domain, transformed = build_domain_fn(base_domain, value)
        if transformed != value:
            print(f"  valor transformat: {transformed!r}")
        print(f"  domain           : {domain}")

        result = erp_lead_obj.search(domain, limit=1)
        if result:
            print(f"  resultat         : {result} ✓ MATCH")
            print(f"\n→ Primera estratègia que fa match: [{label}] — s'aturaria aquí.")
            print("=" * 60)
            return

        print(f"  resultat         : [] ✗ NO MATCH")

        # Search without crm_lead_id=0 to detect false negatives
        domain_no_filter = [c for c in domain if c != ('crm_lead_id', '=', 0)]
        result_no_filter = erp_lead_obj.search(domain_no_filter)
        if result_no_filter:
            if is_mock and mock_leads is not None:
                matching = [l for l in mock_leads if l['id'] in result_no_filter]
                crm_ids = [l.get('crm_lead_id') for l in matching]
            else:
                fields = ['id', 'crm_lead_id']
                matching = erp_lead_obj.read(result_no_filter, fields)
                crm_ids = [m.get('crm_lead_id') for m in matching]

            print(f"  ⚠  Sense filtre crm_lead_id=0 → trobats: {result_no_filter}")
            print(f"     crm_lead_id actuals al ERP    : {crm_ids}")
            print(f"     → Causa probable: el lead ERP ja té crm_lead_id assignat")

    print("\n→ Cap estratègia ha fet match.")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def debug_lead(lead_data, erp_leads):
    """
    Debug matching strategies using a local mock (no ERP connection needed).

    Args:
        lead_data (dict): Odoo lead fields. Keys: som_cups, vat, email_from, phone
        erp_leads (list[dict]): Mock ERP leads. Each dict must include: id,
            crm_lead_id, and the relevant search fields (cups, titular_vat,
            titular_email, titular_phone).
    """
    mock = MockErpLeadObj(erp_leads)
    _debug_with_obj(lead_data, mock, is_mock=True, mock_leads=erp_leads)


def debug_lead_erp(lead_data, erp_conn):
    """
    Debug matching strategies against a real ERP via erppeek.

    Args:
        lead_data (dict): Odoo lead fields. Keys: som_cups, vat, email_from, phone
        erp_conn (dict): erppeek connection params.
            Keys: server, db, user, password
            Example: {
                'server': 'http://erp.example.com:8069',
                'db': 'my_db',
                'user': 'admin',
                'password': 'secret',
            }
    """
    from erppeek import Client
    print(f"Connectant a {erp_conn['server']} / {erp_conn['db']} ...")
    c = Client(**erp_conn)
    erp_lead_obj = c.model('giscedata.crm.lead')
    print("Connexió OK\n")
    _debug_with_obj(lead_data, erp_lead_obj, is_mock=False)


# ---------------------------------------------------------------------------
# Example
# ---------------------------------------------------------------------------

if __name__ == '__main__':

    # # Per obtenir dades reals d'un lead d'Odoo al seu shell
    # lead_id = 123  # ID del lead que vols debugar
    # lead = env['crm.lead'].browse(lead_id)
    # lead_data = {
    #     'som_cups': lead.som_cups,
    #     'vat': lead.vat,
    #     'email_from': lead.email_from,
    #     'phone': lead.phone,
    # }

    lead_data = {
        'som_cups': 'ES0031406533910001JN0F',
        'vat': '12345678Z',
        'email_from': 'example@example.com',
        'phone': '+34 600 000 000',
    }

    # Mock example
    erp_leads = [
        {'id': 1, 'cups': 'ES0031406533910001JN', 'titular_vat': 'ES12345678Z',
         'titular_email': '', 'titular_phone': '', 'crm_lead_id': 0},
        {'id': 2, 'cups': 'ES0099999999990001XX', 'titular_vat': 'ES87654321B',
         'titular_email': 'OTHER@EXAMPLE.COM', 'titular_phone': '612345678',
         'crm_lead_id': 42},
    ]
    debug_lead(lead_data, erp_leads)

    # Real ERP example (uncomment and fill credentials):
    # erp_conn = {
    #     'server': 'http://erp.example.com:8069',
    #     'db': 'my_db',
    #     'user': 'admin',
    #     'password': 'secret',
    # }
    # debug_lead_erp(lead_data, erp_conn)
