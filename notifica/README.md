# notifica - Unified Communication Log

Centralised communication log for Odoo. Captures emails sent from Odoo
and communications pushed via API into a dedicated `comm.log` model.

## Capture Rules

The module does **not** create any rules on install — configure them
explicitly via the UI at **Contacts > Configuration > Communication Log Rules**.

Rules tell the system which source models to watch for outgoing emails.
When an email is sent from a document that matches an active rule, a
`comm.log` entry is created automatically.

Examples of useful rules:

| Model | Partner Field | Description |
|---|---|---|
| `crm.lead` | `partner_id` | Emails from CRM opportunities |
| `sale.order` | `partner_id` | Emails from sales orders |
| `helpdesk.ticket` | `partner_id` | Emails from helpdesk tickets |
| `project.task` | `partner_id` | Emails from project tasks |
| `account.move` | `partner_id` | Emails from invoices |

The `partner_field_name` tells the system which field on the source
document holds the partner relation. Most Odoo models use `partner_id`.

## API

`POST /api/v1/comm/log`

Accepting external communication logs. Requires an API token set at
**Technical > System Parameters > `comm_log.api_token`**.

Full API reference: see `schemas.py` for request/response models.

## Dependencies

- `pydantic>=2.0` — required (API request/response validation)
