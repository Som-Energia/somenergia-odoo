# pbx_cti

Odoo 16 Community module that receives an inbound call webhook from an Irontec PBX and automatically opens the caller's partner form in the Odoo session of the user assigned to the ringing extension.

## How it works

```
Irontec PBX (webhook POST)
  → POST /pbx/ringring
    → validates API key
    → resolves extension → res.users (field: pbx_extension)
    → resolves phone → res.partner (fields: phone / mobile)
    → pushes via bus.bus to the user's browser session
      → OWL service opens the partner form
```

## Configuration

### 1. Set the API key

Go to **Settings → Technical → System Parameters** and create:

| Key | Value |
|-----|-------|
| `pbx_cti.api_key` | `your-secret-token` |

### 2. Assign a PBX extension to each user

Go to **Settings → Users → [user] → PBX / CTI → PBX Extension** and set the extension number (e.g. `201`).

### 3. Ensure partners have a phone number

The lookup is done against the `phone` and `mobile` fields of `res.partner`.

## Webhook endpoint

```
POST /pbx/ringring
Content-Type: application/x-www-form-urlencoded
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `apikey` | yes | Must match `pbx_cti.api_key` system parameter |
| `phone` | yes | Caller's phone number (handles `+34`, `0034` and spaces) |
| `extension` | yes | Extension that received the call |
| `callid` | no | PBX call identifier |

### Example with curl

```bash
curl -X POST https://your-odoo/pbx/ringring \
  -d "apikey=your-secret-token" \
  -d "phone=34931234567" \
  -d "extension=201" \
  -d "callid=test-001"
```

### Example with Insomnia

- **Method:** `POST`
- **URL:** `https://your-odoo/pbx/ringring`
- **Body:** `Form URL Encoded`

| Key | Value |
|-----|-------|
| `apikey` | `your-secret-token` |
| `phone` | `34931234567` |
| `extension` | `201` |
| `callid` | `test-001` |

## Response codes

| Response | Meaning |
|----------|---------|
| `{"result": "ok", "partner_id": ..., "partner_name": ...}` | Call processed, partner found and browser notified |
| `{"result": "no_user", "extension": ...}` | No user has that extension assigned |
| `{"result": "no_partner", "phone": ...}` | No partner found with that phone number |
| `{"error": "unauthorized"}` | Invalid or missing API key (HTTP 401) |
| `{"error": "missing_params", ...}` | Missing `phone` or `extension` (HTTP 400) |

## Dependencies

- `base`
- `bus`
