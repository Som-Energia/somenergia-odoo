# Módulo `notifica` — Odoo 16 Community

## 📋 ¿Qué es?

`notifica` es un **módulo de registro de comunicaciones unificado** para Odoo. Centraliza en un modelo propio (`comm.log`) todas las comunicaciones que ocurren con un contacto, tanto las **salientes desde Odoo** (emails) como las **entrantes desde sistemas externos** vía API.

Depende de `base`, `mail` y `contacts`, y requiere **Pydantic ≥ 2.0** para la validación de la API REST.

---

## 🏗️ Arquitectura: modelos

### 1. `comm.log` — El corazón del módulo

Modelo principal que almacena **cada comunicación** con un contacto.

| Campo | Tipo | Descripción |
|---|---|---|
| `partner_id` | Many2one res.partner | Contacto (requerido, índice) |
| `date` | Datetime | Fecha (por defecto ahora, índice) |
| `subject` | Char | Asunto |
| `body_html` | Html | Cuerpo HTML completo |
| `source_type` | Selection | `internal` (desde Odoo) o `external` (desde API) |
| `origin_app` | Selection | `odoo`, `mailchimp`, `ov` |
| `status` | Selection | `outgoing`, `sent`, `failed`, `bounced` |
| `source_message_id` | Many2one mail.message | Enlace al mensaje original de Odoo |
| `source_model` | Char | Modelo técnico del documento origen (p.ej. `crm.lead`) |
| `source_res_id` | Integer | ID del documento origen |
| `external_ref_id` | Char | ID de referencia del sistema externo |
| `lang` | Char | Código ISO del idioma (`es_ES` por defecto) |
| `author_name` / `author_email` | Char | Metadata del remitente |
| `recipient_email` | Char | Email real del destinatario |
| `failure_reason` | Text | Causa del fallo (para `status = failed`) |

**Constraint SQL**: `UNIQUE(source_message_id, partner_id)` — no permite duplicar el mismo mensaje para el mismo partner.

#### Métodos destacados

**`_get_partner_scope(partner, include_children=False)`**

Resuelve el **ámbito bidireccional** de contactos:
- Si el partner es **padre** (tiene hijos), los incluye.
- Si el partner es **hijo** (tiene `parent_id`), incluye al padre y todos los hermanos.
- Así una comunicación es visible desde todas las "puntas" de la relación comercial.

**`action_retry()`**

Recupera el `mail.mail` original en estado `exception` y lo pone otra vez en `outgoing`. Solo funciona si `status == 'failed'`.

**`action_resend()`**

Reenvía la comunicación usando el `body_html` almacenado. Crea un NUEVO `comm.log` hijo con prefijo `[RESEND]` para trazabilidad completa.

---

### 2. `comm.log.rule` — Reglas de captura

Le dice al sistema **qué modelos observar** para capturar emails salientes automáticamente.

| Campo | Descripción |
|---|---|
| `model_id` | Many2one ir.model — modelo a observar (único, constraint) |
| `active` | Booleano — activa/desactiva la regla |
| `partner_field_name` | Char — campo del modelo que contiene el partner (p.ej. `partner_id`, `customer_id`) |
| `include_child_contacts` | Booleano — si se expande al ámbito bidireccional |
| `description` | Char — descripción libre |

Tiene una **validación** (`_check_partner_field`) que verifica que `partner_field_name` existe realmente como campo en el modelo, evitando reglas rotas.

> ⚠️ No se crea ninguna regla por defecto al instalar. Hay que configurarlas explícitamente desde *Contactos → Configuración → Capture Rules*.

---

### 3. Herencia de `mail.message`

Añade el campo `is_external_log` (booleano) para marcar los mensajes que llegan desde la API externa y distinguirlos de los mensajes normales del chatter.

---

### 4. Herencia de `mail.mail` — El hook (`mail_mail_hook.py`)

**Aquí ocurre la magia de captura automática**. Sobrescribe `_postprocess_sent_message()`:

1. Se ejecuta **después** de que Odoo envía un email.
2. Busca una `comm.log.rule` activa para el modelo del documento origen.
3. Si encuentra regla, resuelve el partner desde el documento.
4. **Ignora notificaciones del sistema** (`message_type` en `notification`, `user_notification`).
5. Determina si fue éxito (`sent`) o fallo (`failed`) según `mail.state`.
6. Expande el ámbito de partners según la regla (`_get_partner_scope`).
7. Crea un `comm.log` por cada partner en el ámbito — o actualiza el existente si estaba en `outgoing` (para finalizar un retry).
8. Es **idempotente**: si ya existe un `comm.log` para ese `(source_message_id, partner_id)`, lo salta.

---

### 5. Herencia de `res.partner`

Añade:
- `comm_log_ids` — One2many a `comm.log` para ver las comunicaciones desde el formulario del contacto.
- `comm_log_count` — Entero computado almacenado para el smart button.

---

## 🌐 API REST

**Endpoint**: `POST /api/v1/comm/log`

### Autenticación

Por **token en header** `X-API-Key`. El token se configura en *Ajustes → Parámetros del Sistema → `comm_log.api_token`*.

El mixin `ApiAuthMixin` (reutilizable para otros controladores) verifica:
1. Que el token exista en `ir.config_parameter`.
2. Que coincida con el header.

### Request (validado con Pydantic)

```json
{
  "email": "cliente@example.com",
  "subject": "Campaña Mayo 2026",
  "body_html": "<p>Contenido</p>",
  "origin_app": "mailchimp",
  "external_msg_id": "camp-123",
  "lang": "es_ES"
}
```

Campos:
| Campo | Tipo | Obligatorio | Default |
|---|---|---|---|
| `email` | string | ✅ Sí | — |
| `subject` | string | ❌ No | `"External Communication"` |
| `body_html` | string | ❌ No | `""` |
| `origin_app` | string | ❌ No | `"odoo"` |
| `external_msg_id` | string | ❌ No | `""` |
| `lang` | string | ❌ No | `"es_ES"` (validado contra `es_ES`, `ca_ES`, `gl_ES`, `eu_ES`) |

### Response (exitosa)

```json
{
  "status": "success",
  "message_id": 42,
  "comm_log_id": 99
}
```

### Response (error)

```json
{
  "status": "error",
  "message": "Validation failed",
  "errors": {
    "email": "field required"
  }
}
```

### Flujo completo del controller

1. Parsear JSON del body.
2. Verificar API token.
3. Validar payload con Pydantic (`CommLogCreateRequest`).
4. Resolver el partner por email (búsqueda exacta, con `sudo`).
5. Construir el body HTML con un **badge** visual que indica el origen (`Logged via MAILCHIMP | External Ref ID: camp-123`).
6. Crear un `mail.message` en el chatter del partner (con `is_external_log = True`).
7. Crear un `comm.log` con `source_type = 'external'` y el `origin_app` indicado.

---

## 🖥️ Vistas e interfaz de usuario

### Formulario de contacto (`res.partner`)

- **Smart button** "Communications" con contador en el `button_box`.
- **Pestaña "Communications"** en el notebook con lista de los últimos 20 registros.

### `comm.log` — Vista dedicada

- **Árbol**: fecha, contacto, asunto, source_type, origin_app, status, recipient_email.
- **Formulario**: todos los campos + botones **Resend** (para enviados) y **Retry** (para fallidos).
- **Búsqueda**: filtros por Internal/External, agrupaciones por source_type, origin_app, partner.

### `comm.log.rule` — Configuración

- Solo visible para usuarios del grupo `base.group_system` (técnicos/administradores).
- Accesible desde *Contactos → Configuración → Capture Rules*.
- Formulario simple: modelo, campo partner, incluir hijos, activo, descripción.

---

## 🔒 Seguridad

| Modelo | Grupo | Permisos |
|---|---|---|
| `comm.log` | Usuario interno (base.group_user) | CRUD (sin borrar) |
| `comm.log` | Administrador (base.group_system) | CRUD completo |
| `comm.log.rule` | Administrador (base.group_system) | CRUD completo |

---

## 🔄 Migración (`16.0.0.2/post-migrate.py`)

Al actualizar el módulo, el script de migración **backfillea** `comm.log` desde emails existentes en `mail.message`:
- De `res.partner` (siempre).
- De `crm.lead` (si el módulo `crm` está instalado).
- Solo mensajes con `message_type = 'email'` y que tengan body.
- Salta los que ya tienen un `comm.log` asociado.

---

## 🧪 Tests

4 archivos de test con cobertura sólida:

| Archivo | Qué prueba |
|---|---|
| `test_schemas.py` | Validación Pydantic (request, errores, defaults, subclass check) |
| `test_comm_log.py` | Creación de logs, defaults, constraint de unicidad, ámbito bidireccional de partners |
| `test_comm_log_rule.py` | Creación, unicidad, validación de campos existentes |
| `test_api.py` | Autenticación (token ausente/erróneo/válido), validación (email faltante, lang inválido), creación exitosa con `HttpCase` real |

---

## 💡 Resumen funcional

**`notifica`** es un **hub de comunicaciones** que:

1. **Captura automáticamente** los emails que Odoo envía desde cualquier documento (CRM, ventas, facturas, proyectos...) siempre que exista una regla activa para ese modelo.
2. **Registra comunicaciones externas** vía API REST autenticada, permitiendo que sistemas como Mailchimp o plataformas propias (`ov`) dejen constancia de sus envíos en Odoo.
3. **Unifica** todo en `comm.log` sin depender del chatter nativo de Odoo, que es efímero y mezcla notificaciones del sistema con comunicaciones reales.
4. **Permite reenvío y reintento** directo desde el registro de comunicación.
5. **Respeta la estructura de contactos** con el ámbito bidireccional: si una empresa tiene 3 contactos hijo, una comunicación enviada a uno es visible desde los 3 y desde la empresa matriz.

El nombre **"notifica"** (italiano para "notifica") refleja su propósito: ser el registro de **todo lo que se notifica** a un contacto, venga de donde venga.
