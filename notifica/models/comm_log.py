# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import UserError

from ..config import ORIGIN_APP_CHOICES


class CommLog(models.Model):
    _name = 'comm.log'
    _description = 'Communication Log'
    _order = 'date DESC'
    _rec_name = 'subject'

    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        required=True,
        index=True,
        ondelete='cascade',
    )
    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        index=True,
    )
    subject = fields.Char(string='Subject')
    body_html = fields.Html(
        string='Content',
        help='Full HTML body. Stored for resend capability.',
    )
    source_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
    ],
        string='Source Type',
        required=True,
        default='internal',
    )
    origin_app = fields.Selection(
        ORIGIN_APP_CHOICES,
        string='Origin App',
        required=True,
        default='odoo',
    )
    status = fields.Selection([
        ('outgoing', 'Outgoing'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ],
        string='Status',
        required=True,
        default='sent',
    )

    # Link to the original Odoo mail.message
    source_message_id = fields.Many2one(
        'mail.message',
        string='Original Message',
        help='Original mail.message this log originates from.',
    )

    # Source document where this communication originated (crm.lead, sale.order, etc.)
    source_model = fields.Char(
        string='Source Document Model',
        help='Technical model name of the source document.',
    )
    source_res_id = fields.Integer(
        string='Source Document ID',
        help='ID of the source document.',
    )

    # External system reference
    external_ref_id = fields.Char(
        string='External Reference ID',
        help='Campaign or transaction ID from the external system.',
    )

    # Communication language (ISO locale code)
    lang = fields.Char(
        string='Language',
        default='es_ES',
        help='ISO locale code for the communication language.',
    )

    # Sender and recipient metadata
    author_name = fields.Char(string='Author Name')
    author_email = fields.Char(string='Author Email')
    recipient_email = fields.Char(string='Recipient Email')

    # Failure tracking (for failed email sends)
    failure_reason = fields.Text(string='Failure Reason')

    @api.model
    def _get_partner_scope(self, partner, include_children=False):
        """Resolve the full partner scope for a communication.

        Returns a list of ``res.partner`` recordsets to create logs for.
        The first entry is always the source partner itself.

        When ``include_children`` is enabled, the scope expands
        bidirectionally:

        * If the partner is a **parent** (has children), all child
          contacts are included so the communication is visible from
          every supply point.
        * If the partner is a **child** (has a commercial parent),
          the parent and all siblings are included so the communication
          is visible from the main account and every other related
          supply point.

        The ``recipient_email`` on each created log MUST reflect the
        **actual** recipient regardless of which partner's chatter it
        appears under — use the source partner's email for all scope
        entries.
        """
        partners = partner
        if not include_children:
            return partners

        parent = partner.commercial_partner_id or partner.parent_id
        if parent and parent != partner:
            # Partner is a child — include parent and all siblings
            partners = partners | parent
            for child in parent.child_ids:
                if child != partner and child != parent:
                    partners = partners | child
        else:
            # Partner is its own commercial entity — include its children
            for child in partner.child_ids:
                if child != partner:
                    partners = partners | child

        return partners

    _sql_constraints = [
        (
            'unique_partner_message',
            'UNIQUE(source_message_id, partner_id)',
            'A communication log already exists for this partner and message.',
        ),
    ]

    def action_retry(self):
        """Re-queue the original ``mail.mail`` for retry.

        Only works for failed communications that still have an
        associated ``mail.mail`` in ``'exception'`` state.
        """
        self.ensure_one()

        if self.status != 'failed':
            raise UserError(
                _('Only failed communications can be retried.')
            )

        if not self.source_message_id:
            raise UserError(
                _('No source message linked to this communication.')
            )

        mail = self.env['mail.mail'].search([
            ('mail_message_id', '=', self.source_message_id.id),
            ('state', '=', 'exception'),
        ], limit=1)
        if not mail:
            raise UserError(
                _('No failed email found to retry for this communication.')
            )

        mail.write({'state': 'outgoing'})
        self.write({'status': 'outgoing'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Retry initiated'),
                'message': _('The email has been queued for retry.'),
                'sticky': False,
                'type': 'success',
            },
        }

    def action_resend(self):
        """Resend this communication to the partner using the stored body_html.

        Creates a new ``mail.mail`` with ``[RESEND]`` prefix and sends it.
        The resulting child ``comm.log`` is linked to the new
        ``mail.message`` via ``source_message_id`` for full traceability.
        """
        self.ensure_one()

        if not self.body_html:
            raise UserError(
                _('This log entry has no content to resend.')
            )

        partner = self.partner_id
        if not partner.email:
            raise UserError(
                _('Contact %s does not have a valid email address.')
                % partner.display_name
            )

        mail_values = {
            'subject': '[RESEND] %s' % (self.subject or 'Communication'),
            'body_html': self.body_html,
            'email_to': partner.email,
            'reply_to': self.env.user.email_formatted
                        or self.env.company.email,
            'model': 'res.partner',
            'res_id': partner.id,
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

        # Create child log entry for tracking, linked to the new message
        child_vals = {
            'partner_id': partner.id,
            'subject': _('Resent: %s') % (self.subject or 'Communication'),
            'body_html': self.body_html,
            'source_type': 'internal',
            'origin_app': 'odoo',
            'status': 'sent',
            'author_email': self.env.user.email_formatted,
            'recipient_email': partner.email,
        }
        if mail.mail_message_id:
            child_vals['source_message_id'] = mail.mail_message_id.id
        self.env['comm.log'].create(child_vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Email resent'),
                'message': _('Communication resent to %s') % partner.email,
                'sticky': False,
                'type': 'success',
            },
        }
