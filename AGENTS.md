# AGENTS.md

This repository contains custom and third-party addons for **Odoo Community 16** used by **Som Energia**.

## Purpose

- Maintain Odoo 16 addons in a single repo.
- Combine Som Energia custom business modules with community/vendor addons.
- Keep each addon self-contained, installable, and testable through standard Odoo addon conventions.

## Repository layout

- `*/__manifest__.py` — each top-level addon is an Odoo module.
- `somenergia_custom/` — largest Som Energia custom module; HR, timesheets, projects, appraisals, surveys.
- `som_crm/` — CRM customizations, sync flows, mail and lead behavior.
- `odoo_callinfo/` — CallInfo / Tomàtic integration.
- `som_event/`, `som_survey/`, `som_google_sheets_integration/` — domain-specific extensions.
- `hr_employee_multidepartment/`, `web_pivot_computed_measure/`, `employee_documents_expiry/` — community/vendor addons kept in-repo.
- `.agents/` — project-specific agent registry and skills.
- `scripts/` — local helper/config assets.

## Common addon structure

Most addons follow normal Odoo patterns:

- `models/` — business logic
- `views/` — XML views
- `security/` — ACLs and record rules
- `data/` — data loading
- `wizard/` or `wizards/` — transient flows
- `report/` or `reports/` — reporting definitions
- `tests/` — Odoo test cases
- `i18n/` — translations
- `static/` — web assets / descriptions
- `migrations/` — migration steps when present

Always inspect `__manifest__.py` first before changing a module. It defines dependencies, loaded XML/CSV files, and module scope.

## Stack and dependencies

- Target platform: **Odoo Community 16**
- Main language: **Python**
- UI/config layer: **XML**
- Frontend assets may appear as **JS/CSS/SCSS/XML** in web-oriented addons
- Translation files: **i18n**
- Python dependencies are declared in:
  - repo root `requirements.txt`
  - addon-level `requirements.txt` when needed (example: `som_crm/requirements.txt`)

Examples confirmed in this repo:

- Root dependencies include `gspread` and `pyOpenSSL`.
- Tests use Odoo's `TransactionCase` and `tagged(...)` decorators.

## How to work safely in this repo

1. **Treat each top-level directory as a separate addon.**
2. **Do not move files referenced by `data` in `__manifest__.py` without updating the manifest.**
3. **Preserve Odoo naming and loading order.** XML/security/data file order matters.
4. **Prefer small, module-local changes.** Avoid cross-addon edits unless the dependency chain is explicit.
5. **Check existing tests in the same addon first** and extend them instead of inventing a new testing style.
6. **Do not expose secrets.** There is local config under `scripts/` that must be treated as sensitive.

## Testing guidance

Project-local agent registry documents the preferred Odoo test flow:

- Activate environment: `pyenv activate odoo160`
- Base pattern:

```bash
ODOO_ROOT=/path/to/odoo160 && python "$ODOO_ROOT/src/core/odoo-bin" \
  -c "$ODOO_ROOT/conf/odoo_som.conf" \
  --stop-after-init \
  --log-level=test \
  -d <database> \
  -u <module> \
  --test-enable
```

- Optional filtering:

```bash
--test-tags "<spec1>,<spec2>"
```

Before proposing a test command, confirm:

- target database
- target addon name
- whether tags are needed
- whether the environment `odoo160` exists on the machine

## Conventions for coding agents

### Read first

Before editing an addon, read:

1. that addon's `__manifest__.py`
2. the relevant `models/`, `views/`, or `tests/`
3. `.agents/skill-registry.md` for project-specific workflow rules

### Branch / commit / PR conventions

The project registry currently defines these conventions:

- Branch format: `<TYPE>_<description>`
- Branch types: `IMP_`, `FIX_`, `MOD_`, `ADD_`, `REF_`, `TEST_`, `DOCS_`, `CI_`
- Commit format: `<emoji> <description>`
- PR descriptions: in **Catalan**, filling all template sections

If you are acting as an automated agent, verify these conventions before creating Git artifacts.

Important: `.agents/skill-registry.md` references some convention files under `.github/docs/` and `pull_request_template.md`, but those files were not present in this checkout when this guide was created. Treat those references as potentially stale until verified.

### Odoo-specific editing rules

- Keep model names, XML ids, and security ids stable unless renaming is required everywhere.
- When adding fields used in views/security/reports, update every affected layer.
- When changing business behavior, search the addon's `tests/` directory for coverage gaps.
- For imported/community addons, minimize divergence unless Som Energia explicitly owns the customization.

## Useful discovery commands

```bash
# List addon manifests
rg --files -g '__manifest__.py'

# Find tests
rg --files -g 'tests/*.py' -g 'tests/**/*.py'

# Find Python dependencies
rg --files -g 'requirements.txt'
```

## Source evidence used for this guide

- `requirements.txt`
- `somenergia_custom/__manifest__.py`
- `som_crm/__manifest__.py`
- `som_crm/requirements.txt`
- `som_crm/tests/test_crm_lead.py`
- `som_crm/`
- `somenergia_custom/`
- `.agents/skill-registry.md`
