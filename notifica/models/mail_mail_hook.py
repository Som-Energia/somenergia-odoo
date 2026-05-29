# -*- coding: utf-8 -*-
from odoo import models
import logging

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = 'mail.mail'

    # ---------------------------------------------------------------
    # PUBLIC HOOK — entry point called by Odoo after sending emails
    # ---------------------------------------------------------------

    def _postprocess_sent_message(self, success_pids, failure_reason=False, failure_type=None):
        """Capture sent (and failed) emails into ``comm.log``.

        Processes **all** mails in ``self``:

        * ``mail.state == 'sent'`` → ``comm.log`` with ``status='sent'``.
        * ``mail.state == 'exception'`` → ``comm.log`` with
          ``status='failed'`` and the ``failure_reason`` stored.

        Idempotent: if ``(source_message_id, partner_id)`` already exists
        with ``status='outgoing'`` (retry in progress), updates it to the
        actual delivery status. Otherwise skips silently.

        .. note::

           ``success_pids`` (partner IDs) is **not** used to determine
           success — Odoo OCB sets ``mail.state`` **before** calling this
           hook, so we rely on that instead.
        """
        res = super()._postprocess_sent_message(
            success_pids, failure_reason=failure_reason, failure_type=failure_type,
        )

        for mail in self:
            self._log_mail_processing(mail)

            # ── Guard: is this mail eligible for capture? ──────────
            rule = self._get_active_rule(mail)
            if not rule:
                continue

            partner = self._resolve_partner(mail, rule)
            if not partner:
                continue

            message = mail.mail_message_id
            if not message or self._is_system_notification(message):
                continue

            # ── Resolve status and build log payload ──────────────
            status, failure_reason = self._resolve_delivery_status(mail)
            base_vals = self._build_log_values(mail, message, partner)
            scope = self._get_partner_scope(partner, rule)

            # ── Idempotent upsert for each partner in scope ──────
            self._upsert_logs_for_scope(mail, message, scope, status, failure_reason, base_vals)

        return res

    # ---------------------------------------------------------------
    # GUARD HELPERS — decide whether to capture this mail
    # ---------------------------------------------------------------

    @staticmethod
    def _log_mail_processing(mail):
        """Log the mail being processed (debug level)."""
        _logger.debug(
            "comm.log hook: mail id=%s state=%s model=%s res_id=%s msg_type=%s",
            mail.id, mail.state, mail.model, mail.res_id,
            mail.mail_message_id.message_type if mail.mail_message_id else None,
        )

    def _get_active_rule(self, mail):
        """Return the active capture rule for this mail's model, or ``None``.

        Skips mails that have no model or res_id (orphan records),
        and mails whose source model has no active rule defined.
        """
        if not mail.model or not mail.res_id:
            return None

        rule = self.env['comm.log.rule'].search([
            ('model_id.model', '=', mail.model),
            ('active', '=', True),
        ], limit=1)
        if not rule:
            _logger.debug("comm.log: no active rule for model %s", mail.model)

        return rule

    def _resolve_partner(self, mail, rule):
        """Resolve the partner from the source document linked to this mail.

        If the source document does not exist, or the partner field is
        empty, returns ``None`` and the mail is silently skipped.
        """
        source = self.env[mail.model].browse(mail.res_id)
        if not source.exists():
            _logger.debug("comm.log: source %s/%s not found", mail.model, mail.res_id)
            return None

        partner = source if mail.model == 'res.partner' else source[rule.partner_field_name]
        if not partner or not partner.exists():
            _logger.debug(
                "comm.log: no partner resolved for %s/%s (field '%s')",
                mail.model, mail.res_id, rule.partner_field_name,
            )
            return None

        return partner

    @staticmethod
    def _is_system_notification(message):
        """Return ``True`` if the message is a system notification, not a real communication.

        Filters out assignment alerts, automated reminders, and other
        system-generated messages that should NOT create comm.log entries.
        """
        return message.message_type in ('notification', 'user_notification')

    # ---------------------------------------------------------------
    # DATA HELPERS — extract delivery status and log values
    # ---------------------------------------------------------------

    @staticmethod
    def _resolve_delivery_status(mail):
        """Determine delivery status from ``mail.state``.

        Returns a ``(status, failure_reason)`` tuple:

        * ``mail.state == 'sent'`` → ``('sent', None)``
        * ``mail.state == 'exception'`` → ``('failed', <reason>)``

        ``failure_reason`` is set by Odoo **before** calling this hook.
        """
        is_success = mail.state == 'sent'
        status = 'sent' if is_success else 'failed'
        reason = mail.failure_reason or False
        return status, reason

    @staticmethod
    def _build_log_values(mail, message, partner):
        """Build the base ``comm.log`` creation dict from mail + message metadata.

        The ``recipient_email`` always uses the **actual** recipient
        (the partner's email), not the scope partner's email.
        """
        return {
            'subject': mail.subject or message.subject or '',
            'body_html': mail.body_html or message.body or '',
            'author_email': message.author_id.email_formatted or '',
            'recipient_email': partner.email or '',
        }

    # ---------------------------------------------------------------
    # SCOPE HELPERS — expand to related partners
    # ---------------------------------------------------------------

    def _get_partner_scope(self, partner, rule):
        """Expand the partner scope according to the rule's settings.

        Delegates to ``comm.log._get_partner_scope`` for the actual
        bidireccional logic (parent → children, child → parent + siblings).
        """
        return self.env['comm.log']._get_partner_scope(
            partner, rule.include_child_contacts,
        )

    # ---------------------------------------------------------------
    # PERSISTENCE — create or update comm.log entries
    # ---------------------------------------------------------------

    def _upsert_logs_for_scope(self, mail, message, scope, status, failure_reason, base_vals):
        """For each partner in scope, create or update a ``comm.log``.

        * If a log already exists for ``(message, scope_partner)`` and its
          status is ``'outgoing'`` (a retry was in progress), it is updated
          to the final delivery status.
        * If a log already exists with any other status, it is **skipped**
          (idempotent: we do NOT overwrite past deliveries).
        * Otherwise, a new ``comm.log`` is created.
        """
        for scope_partner in scope:
            existing = self.env['comm.log'].search([
                ('source_message_id', '=', message.id),
                ('partner_id', '=', scope_partner.id),
            ], limit=1)

            if existing:
                self._try_finalise_retry(existing, status, failure_reason)
                continue

            self._safe_create_log(mail, message, scope_partner, status, failure_reason, base_vals)

    @staticmethod
    def _try_finalise_retry(existing_log, status, failure_reason):
        """If the existing log was in ``'outgoing'`` (retry), update it to final status.

        Otherwise do nothing — the log already reflects a past delivery.
        """
        if existing_log.status == 'outgoing':
            existing_log.write({
                'status': status,
                'failure_reason': failure_reason if status == 'failed' else None,
            })

    def _safe_create_log(self, mail, message, partner, status, failure_reason, base_vals):
        """Create a ``comm.log`` entry, catching and logging any unexpected errors.

        Uses the base values extracted from the mail/message and adds
        the partner-scoped fields.
        """
        log_vals = {
            **base_vals,
            'partner_id': partner.id,
            'source_type': 'internal',
            'origin_app': 'odoo',
            'status': status,
            'source_message_id': message.id,
            'source_model': mail.model,
            'source_res_id': mail.res_id,
            'failure_reason': failure_reason if status == 'failed' else None,
        }

        try:
            self.env['comm.log'].create(log_vals)
            _logger.debug("comm.log created for mail %s (status=%s)", mail.id, status)
        except Exception as exc:
            _logger.warning(
                "Failed to create comm.log for message %s / partner %s: %s",
                message.id, partner.id, exc,
            )
