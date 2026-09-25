# Partner Communication Timeline

Odoo 16 Community addon to show a transversal communication history from a contact (`res.partner`).

The module adds:

- A smart button on the contact form.
- A `Communications` tab with the latest messages.
- A full communication list view over `mail.message`.
- A configuration menu under Contacts > Configuration > Communication Timeline.
- Default support for `crm.lead` and `helpdesk.ticket` when those models are installed.
- Optional rules to include other models with a `Many2one` field pointing to `res.partner`.

## What is included in the timeline

For a contact, the module searches communications related to the commercial partner and its child contacts:

- Messages directly posted on `res.partner` records.
- Messages whose author is one of those partners.
- Messages where one of those partners is a recipient.
- Email messages whose `email_from` contains one of those partner emails.
- Messages posted on configured business documents, such as CRM leads and helpdesk tickets.

By default, only `email` and `comment` message types are shown. This avoids many automatic system notifications.

## Default business document rules

On installation, if the models exist, the module creates rules for:

- `crm.lead` using `partner_id`
- `helpdesk.ticket` using `partner_id`

If those apps are installed later, the module still includes those models automatically when they exist and have a valid `partner_id` field. You can also create rules manually.

## Configuration

Go to:

`Contacts > Configuration > Communication Timeline`

Create a rule with:

- Model: for example `Project Task` (`project.task`)
- Partner field: for example `partner_id`
- Include child contacts: enabled if company-level contacts should include child contact documents

The partner field must be a `Many2one` to `res.partner`.

## Installation

Copy the addon directory into your custom addons path, then update the apps list and install `Partner Communication Timeline`.

Example:

```bash
cp -r partner_communication_timeline /opt/odoo/custom-addons/
./odoo-bin -d your_database -u partner_communication_timeline --stop-after-init
```

## Notes and caveats

This is an MVP intended for staging validation before production use.

Important things to validate with real data:

- Record rules and access rights for CRM/ticket users.
- Whether the `helpdesk.ticket` model in your installation uses `partner_id` or another field name.
- Whether matching by `email_from` creates false positives. Disable it with the system parameter if needed.
- Performance on contacts with very large historical message volumes.

For very large databases, consider adding PostgreSQL indexes or replacing parts of the dynamic domain with a materialized reporting table.
