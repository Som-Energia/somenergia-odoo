# -*- coding: utf-8 -*-

"""
Populate pct_body_text and pct_partner_id for all existing mail.message records.

pct_body_text:
  Uses PostgreSQL regexp_replace to strip HTML tags directly in the DB.

pct_partner_id:
  Resolves the partner directly in SQL for the three known cases:
  - model = res.partner     → res_id is the partner
  - model = crm.lead        → partner_id from crm_lead table
  - model = helpdesk.ticket → partner_id from helpdesk_ticket table
"""

import logging

_logger = logging.getLogger(__name__)

_BATCH_SIZE = 5000

_BODY_TO_TEXT_SQL = """
    btrim(
        regexp_replace(
            regexp_replace(
                coalesce(body, ''),
                '<[^>]*>',
                ' ',
                'g'
            ),
            '\s+',
            ' ',
            'g'
        )
    )
"""


def _populate_body_text_batch(cr, min_id, max_id):
    cr.execute(
        """
        UPDATE mail_message
        SET pct_body_text = {body_to_text}
        WHERE id BETWEEN %s AND %s
          AND pct_body_text IS NULL
        """.format(body_to_text=_BODY_TO_TEXT_SQL),
        (min_id, max_id),
    )


def _populate_partner_id_batch(cr, min_id, max_id):
    cr.execute("""
        UPDATE mail_message mm
        SET pct_partner_id = mm.res_id
        WHERE mm.id BETWEEN %s AND %s
          AND mm.model = 'res.partner'
          AND mm.res_id IS NOT NULL
          AND mm.pct_partner_id IS NULL
    """, (min_id, max_id))

    cr.execute("""
        UPDATE mail_message mm
        SET pct_partner_id = cl.partner_id
        FROM crm_lead cl
        WHERE mm.id BETWEEN %s AND %s
          AND mm.model = 'crm.lead'
          AND mm.res_id = cl.id
          AND mm.pct_partner_id IS NULL
    """, (min_id, max_id))

    cr.execute("""
        UPDATE mail_message mm
        SET pct_partner_id = ht.partner_id
        FROM helpdesk_ticket ht
        WHERE mm.id BETWEEN %s AND %s
          AND mm.model = 'helpdesk.ticket'
          AND mm.res_id = ht.id
          AND mm.pct_partner_id IS NULL
    """, (min_id, max_id))


def migrate(cr, version):
    cr.execute("SELECT min(id), max(id) FROM mail_message")
    row = cr.fetchone()
    if not row or row[0] is None:
        return

    min_id, max_id = row
    _logger.info(
        "Populating pct_body_text and pct_partner_id for mail.message ids %d..%d",
        min_id, max_id,
    )

    batch_start = min_id
    while batch_start <= max_id:
        batch_end = batch_start + _BATCH_SIZE - 1
        _populate_body_text_batch(cr, batch_start, batch_end)
        _populate_partner_id_batch(cr, batch_start, batch_end)
        _logger.info("Processed mail.message ids up to %d / %d", batch_end, max_id)
        batch_start += _BATCH_SIZE
