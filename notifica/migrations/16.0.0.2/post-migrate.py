# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Backfill comm.log entries from existing mail.message records.

    Captures past emails sent from:
    - res.partner chatter (always)
    - crm.lead chatter (if the crm module is installed)
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    models_to_migrate = ['res.partner']

    # Conditionally include crm.lead when the module is available
    if 'crm.lead' in env:
        models_to_migrate.append('crm.lead')
        _logger.info("crm module detected — including crm.lead in migration")
    else:
        _logger.info("crm module not found — skipping crm.lead")

    total_migrated = 0

    for model_name in models_to_migrate:
        messages = env['mail.message'].search([
            ('model', '=', model_name),
            ('message_type', '=', 'email'),
            ('body', '!=', False),
        ], order='date ASC')

        for msg in messages:
            # Skip if comm.log already exists for this source message
            if env['comm.log'].search(
                [('source_message_id', '=', msg.id)], limit=1
            ):
                continue

            # Resolve the partner from the source document
            if model_name == 'res.partner':
                partner = env['res.partner'].browse(msg.res_id)
            else:
                source = env[model_name].browse(msg.res_id)
                partner = source.sudo().partner_id if hasattr(source, 'partner_id') else None

            if not partner or not partner.exists():
                continue

            try:
                env['comm.log'].create({
                    'partner_id': partner.id,
                    'subject': msg.subject or '(no subject)',
                    'body_html': msg.body,
                    'source_type': 'internal',
                    'origin_app': 'odoo',
                    'status': 'sent',
                    'date': msg.date,
                    'source_message_id': msg.id,
                    'source_model': model_name,
                    'source_res_id': msg.res_id,
                    'author_email': msg.author_id.email_formatted or '',
                    'recipient_email': partner.email or '',
                })
                total_migrated += 1
            except Exception as exc:
                _logger.warning(
                    "Failed to migrate mail.message %s: %s", msg.id, exc
                )

    _logger.info(
        "Migration complete: %s comm.log entries created", total_migrated
    )
