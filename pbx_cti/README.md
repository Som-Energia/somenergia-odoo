# pbx_cti

Odoo 16 Community module that receives an inbound call webhook from an Irontec PBX and automatically opens the caller's partner form in the Odoo session of the user assigned to the ringing extension.

## How it works

```
Irontec PBX (webhook POST)
  → POST /api/info/ringring
    → resolves extension → res.users (field: pbx_extension)
    → resolves phone → res.partner (fields: phone / mobile)
    → pushes via bus.bus to the user's browser session
      → OWL service opens the partner form
```

## Authentication

Authentication is handled by nginx (HTTP Basic) before the request reaches Odoo. No additional API key configuration is required at the application level.

## Configuration

### 1. Assign a PBX extension to each user

Go to **Settings → Users → [user] → PBX / CTI → PBX Extension** and set the extension number (e.g. `201`).

### 2. Ensure partners have a phone number

The lookup is done against the `phone` and `mobile` fields of `res.partner`.

## Webhook endpoint

```
POST /api/info/ringring
Content-Type: application/x-www-form-urlencoded
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `phone` | yes | Caller's phone number (handles `+34`, `0034` and spaces) |
| `ext` | yes | Extension that received the call |
| `callid` | no | PBX call identifier |

### Example with curl

```bash
curl -X POST https://your-odoo/api/info/ringring \
  -d "phone=600000000" \
  -d "ext=200" \
  -d "callid=1234567890.100000"
```

### Example with Insomnia

- **Method:** `POST`
- **URL:** `https://your-odoo/api/info/ringring`
- **Body:** `Form URL Encoded`

| Key | Value |
|-----|-------|
| `phone` | `600000000` |
| `ext` | `200` |
| `callid` | `1234567890.100000` |

## Response codes

| Response | Meaning |
|----------|---------|
| `{"result": "ok", "partner_id": ..., "partner_name": ...}` | Call processed, partner found and browser notified |
| `{"result": "no_user", "extension": ...}` | No user has that extension assigned |
| `{"result": "no_partner", "phone": ...}` | No partner found with that phone number |
| `{"error": "missing_params", ...}` | Missing `phone` or `ext` (HTTP 400) |

## Known limitations

- **Phone number matching is basic**: the lookup compares the incoming number (digits only, `+34`/`0034` stripped) directly against the `phone` and `mobile` fields of `res.partner`. Partners whose numbers are stored in a different format (e.g. `+34 600 00 00 00`) will not be found. Proper normalization (e.g. via `base_phone` from OCA) is out of scope for this spike.

## Dependencies

- `base`
- `bus`
