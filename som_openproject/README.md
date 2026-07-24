# Som OpenProject

This module imports OpenProject time entries into Odoo timesheets.

## Configuration

Configure these Odoo server configuration options. They must never be committed to
the repository:

```ini
openproject_api_url = https://example.openproject.com
openproject_api_key = replace-with-an-api-key
```

The API key is sent through OpenProject Basic Auth using `apikey` as the user.

The historical validation scripts are kept under `scripts/open_project/`. Their local,
ignored `.openproject.conf` remains under `somenergia_custom/scripts/open_project/`.
The scripts retain that location as a fallback. The Odoo importer does not read it.

## Schedule

The scheduled action is inactive by default. After validation in a test environment,
activate it to run weekly on Sunday. Every execution, including a manual execution on
another day, imports the Monday-Sunday range of its current week. For example,
execution on 2026-07-26 imports entries dated from 2026-07-20 through 2026-07-26.

The initial next execution is scheduled for 08:00 UTC, which is 10:00 in Spain during
summer time. The business rule is independent of the exact execution hour.

## Matching rules

Only entries with an OpenProject CeCo value are candidates for import. The target
work-package value has priority over the project value:

```text
openproject_work_package_ceco -> openproject_project_ceco
```

The selected value is matched exactly against `project.project.name`. The employee is
matched exactly through `hr.employee.user_id.login` and the OpenProject user login.
Missing or ambiguous employee, project, calendar week, or worked-week matches cause
the entry to be skipped and logged as a warning.

The Odoo timesheet description uses `openproject_work_package_subject`. The
OpenProject time-entry comment remains available in the stored source JSON.

## Immutability and traceability

Every imported entry stores:

- `oproject_entry_id`: immutable OpenProject time-entry ID.
- `oproject_source_data`: normalized JSON data used for the Odoo creation.

`oproject_entry_id` has a partial database unique index for values other than zero.
Re-runs and retries therefore skip already imported entries. Changes or deletions made
later in OpenProject are not synchronized; they must be regularized manually in Odoo.

An OpenProject API failure aborts the cron execution and is logged with its traceback.
It must be retried manually after resolving the connection problem; it is not treated
as a successful weekly import.

## Logging

The import logs its date range, every skipped entry and its reason, and a final count
of read, created, duplicate, and skipped entries. Match warnings include the value
searched; normalized source data is logged only at debug level. API credentials are
never logged.

## Change policy

Update this README whenever a business rule, matching rule, scheduling rule, or
traceability field changes.
