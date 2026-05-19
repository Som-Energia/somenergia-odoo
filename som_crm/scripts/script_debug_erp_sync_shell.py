# -*- coding: utf-8 -*-
# Debug script for _erp_sync matching logic.
# To be executed in Odoo shell to inspect why a lead is not matching in ERP.
#
# Usage (Odoo shell):
#   exec(open('som_crm/scripts/script_debug_erp_sync_shell.py').read())
#
# Then call:
#   debug_lead_shell(env, LEAD_ID)

from erppeek import Client
from odoo.tools import config


def _get_erp_client():
    return Client(
        server=f"{config.get('erp_uri')}:{config.get('erp_port')}",
        db=config.get('erp_dbname'),
        user=config.get('erp_user'),
        password=config.get('erp_pwd'),
    )


STRATEGIES = [
    ('som_cups',   'CUPS',  '_erp_search_by_cups'),
    ('vat',        'VAT',   '_erp_search_by_vat'),
    ('email_from', 'EMAIL', '_erp_search_by_email'),
    ('phone',      'PHONE', '_erp_search_by_phone'),
]


def debug_lead_shell(env, lead_id):
    """
    Debug _erp_sync matching strategies for a single lead using production
    model methods directly.

    Args:
        env: Odoo environment (available as 'env' in Odoo shell)
        lead_id (int): ID of the crm.lead record to debug
    """
    lead = env['crm.lead'].browse(lead_id)
    if not lead.exists():
        print(f"Lead {lead_id} no trobat")
        return

    print("=" * 60)
    print(f"ERP SYNC DEBUG — lead {lead_id}: {lead.name}")
    print("=" * 60)
    print(f"  som_cups   : {lead.som_cups!r}")
    print(f"  vat        : {lead.vat!r}")
    print(f"  email_from : {lead.email_from!r}")
    print(f"  phone      : {lead.phone!r}")
    print()

    print("Connectant al ERP...")
    try:
        c = _get_erp_client()
    except Exception as e:
        print(f"Error de connexió: {e}")
        return
    print("Connexió OK\n")

    erp_lead_obj = c.model('giscedata.crm.lead')
    base_domain = [('crm_lead_id', '=', 0)]

    for lead_field, label, method_name in STRATEGIES:
        value = getattr(lead, lead_field, None)
        print(f"[{label}]")

        if not value:
            print(f"  valor: (buit) → estratègia saltada\n")
            continue

        print(f"  valor: {value!r}")

        domain = list(base_domain)
        strategy_fn = getattr(lead, method_name)
        result = strategy_fn(erp_lead_obj, domain, value)

        # domain has been mutated in-place by the strategy
        print(f"  domain: {domain}")

        if result:
            print(f"  resultat: {result} ✓ MATCH")
            print(f"\n→ Primera estratègia que fa match: [{label}] — s'aturaria aquí.")
            print("=" * 60)
            return

        print(f"  resultat: [] ✗ NO MATCH")

        # Check without crm_lead_id=0 to detect false negatives
        domain_no_filter = [c for c in domain if c != ('crm_lead_id', '=', 0)]
        result_no_filter = erp_lead_obj.search(domain_no_filter)
        if result_no_filter:
            matching = erp_lead_obj.read(result_no_filter, ['id', 'crm_lead_id'])
            crm_ids = [m.get('crm_lead_id') for m in matching]
            print(f"  ⚠  Sense filtre crm_lead_id=0 → trobats: {result_no_filter}")
            print(f"     crm_lead_id actuals al ERP    : {crm_ids}")
            print(f"     → Causa probable: el lead ERP ja té crm_lead_id assignat")
        print()

    print("→ Cap estratègia ha fet match.")
    print("=" * 60)
