# -*- coding: utf-8 -*-
import json
import logging
import re
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urljoin

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import config


_logger = logging.getLogger(__name__)

ISO_DURATION_PATTERN = re.compile(
    r"^PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?$"
)


class OpenProjectClient:
    """Small API v3 client used only by the scheduled importer."""

    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.auth = ("apikey", api_key)
        self.session.headers.update({"Accept": "application/hal+json"})

    def get(self, path_or_url, params=None):
        response = self.session.get(
            urljoin(self.base_url, path_or_url),
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    oproject_entry_id = fields.Integer(
        string="OpenProject time entry ID",
        index=True,
        copy=False,
        readonly=True,
    )
    oproject_source_data = fields.Json(
        string="OpenProject source data",
        copy=False,
        readonly=True,
    )

    def init(self):
        # Odoo stores an empty Integer as 0, so a normal unique constraint would
        # incorrectly allow only one manually created timesheet.
        self._cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            account_analytic_line_oproject_entry_id_uniq
            ON account_analytic_line (oproject_entry_id)
            WHERE oproject_entry_id != 0
        """)

    def write(self, vals):
        protected_fields = {"oproject_entry_id", "oproject_source_data"}
        if protected_fields.intersection(vals):
            for record in self.filtered("oproject_entry_id"):
                if (
                    "oproject_entry_id" in vals
                    and vals["oproject_entry_id"] != record.oproject_entry_id
                ):
                    raise UserError(
                        "The OpenProject time entry ID is immutable after import."
                    )
                if (
                    "oproject_source_data" in vals
                    and vals["oproject_source_data"] != record.oproject_source_data
                ):
                    raise UserError(
                        "The OpenProject source data is immutable after import."
                    )
        return super().write(vals)

    @api.model
    def _get_openproject_week_range(self, execution_date=None):
        """Return the Monday-Sunday range for the week being executed."""
        if execution_date:
            execution_date = fields.Date.to_date(execution_date)
        else:
            execution_date = fields.Date.today()
        date_from = execution_date - timedelta(days=execution_date.weekday())
        return date_from, date_from + timedelta(days=6)

    @api.model
    def _get_openproject_client(self):
        base_url = (config.get("openproject_api_url") or "").strip().strip("\"'")
        api_key = (config.get("openproject_api_key") or "").strip().strip("\"'")
        if not base_url or not api_key:
            _logger.warning(
                "OpenProject import skipped: openproject_api_url or "
                "openproject_api_key is not configured."
            )
            return False
        return OpenProjectClient(base_url, api_key)

    @api.model
    def _openproject_link_id(self, link):
        if not link:
            return False
        try:
            return int(link["href"].rstrip("/").rsplit("/", 1)[-1])
        except (KeyError, TypeError, ValueError):
            return False

    @api.model
    def _openproject_duration_to_hours(self, duration):
        match = ISO_DURATION_PATTERN.fullmatch(duration or "")
        if not match or not any(match.groupdict().values()):
            raise ValueError("Unsupported OpenProject duration: %r" % duration)
        hours = Decimal(match.group("hours") or 0)
        minutes = Decimal(match.group("minutes") or 0)
        seconds = Decimal(match.group("seconds") or 0)
        return float(hours + minutes / 60 + seconds / 3600)

    @api.model
    def _get_openproject_time_entries(self, client, date_from, date_to):
        filters = [{
            "spent_on": {
                "operator": "<>d",
                "values": [date_from.isoformat(), date_to.isoformat()],
            },
        }]
        page = client.get(
            "time_entries",
            params={"pageSize": 200, "filters": json.dumps(filters)},
        )
        while True:
            for entry in page.get("_embedded", {}).get("elements", []):
                spent_on = entry.get("spentOn")
                if spent_on and date_from.isoformat() <= spent_on <= date_to.isoformat():
                    yield entry
            next_page = page.get("_links", {}).get("nextByOffset")
            if not next_page:
                return
            page = client.get(next_page["href"])

    @api.model
    def _get_openproject_resource(self, client, cache, link):
        if not link:
            return {}
        href = link.get("href")
        if not href:
            return {}
        if href not in cache:
            cache[href] = client.get(href)
        return cache[href]

    @api.model
    def _normalize_openproject_entry(self, client, entry, caches):
        links = entry.get("_links", {})
        user_link = links.get("user")
        project_link = links.get("project")
        work_package_link = links.get("workPackage") or links.get("entity")
        user = self._get_openproject_resource(client, caches["users"], user_link)
        project = self._get_openproject_resource(
            client, caches["projects"], project_link
        )
        work_package = self._get_openproject_resource(
            client, caches["work_packages"], work_package_link
        )
        return {
            "openproject_time_entry_id": entry.get("id"),
            "date": entry.get("spentOn"),
            "openproject_hours": entry.get("hours"),
            "unit_amount": self._openproject_duration_to_hours(entry.get("hours")),
            "comment": entry.get("comment", {}).get("raw"),
            "openproject_user_id": self._openproject_link_id(user_link),
            "openproject_user_name": user.get("name") or (user_link or {}).get("title"),
            "openproject_user_login": user.get("login"),
            "employee_work_email": user.get("email"),
            "openproject_project_id": self._openproject_link_id(project_link),
            "openproject_project_name": (project_link or {}).get("title"),
            "openproject_project_ceco": project.get("customField13"),
            "openproject_work_package_id": self._openproject_link_id(work_package_link),
            "openproject_work_package_subject": (work_package_link or {}).get("title"),
            "openproject_work_package_ceco": work_package.get("customField14"),
        }

    @api.model
    def _get_unique_openproject_match(
            self, model_name, domain, entry_id, label, value, source_data):
        records = self.env[model_name].with_context(active_test=False).search(
            domain, limit=2
        )
        if len(records) == 1:
            return records
        _logger.warning(
            "OpenProject entry %s skipped: %s match for %r returned %s records.",
            entry_id,
            label,
            value,
            len(records),
        )
        _logger.debug(
            "OpenProject entry %s normalized source data: %s",
            entry_id,
            json.dumps(source_data, ensure_ascii=False, sort_keys=True),
        )
        return False

    @api.model
    def _prepare_openproject_timesheet_values(self, source_data):
        entry_id = source_data.get("openproject_time_entry_id")
        work_package_ceco = source_data.get("openproject_work_package_ceco")
        project_ceco = source_data.get("openproject_project_ceco")
        project_name = work_package_ceco or project_ceco
        if not project_name or not project_name.strip():
            _logger.warning(
                "OpenProject entry %s skipped: no work-package or project CeCo.",
                entry_id,
            )
            return False

        login = source_data.get("openproject_user_login")
        if not login:
            _logger.warning(
                "OpenProject entry %s skipped: no user login.", entry_id
            )
            return False
        employee = self._get_unique_openproject_match(
            "hr.employee",
            [("user_id.login", "=", login)],
            entry_id,
            "employee",
            login,
            source_data,
        )
        project = self._get_unique_openproject_match(
            "project.project",
            [("name", "=", project_name)],
            entry_id,
            "project",
            project_name,
            source_data,
        )
        if not employee or not project:
            return False

        entry_date = source_data.get("date")
        week, worked_week = self._get_worked_week_info_from_timesheet_date(
            entry_date, employee.id
        )
        if not week or not worked_week:
            _logger.warning(
                "OpenProject entry %s skipped: no calendar or worked week for %s.",
                entry_id,
                entry_date,
            )
            return False
        return {
            "name": source_data.get("openproject_work_package_subject") or "/",
            "date": entry_date,
            "unit_amount": source_data.get("unit_amount"),
            "employee_id": employee.id,
            "project_id": project.id,
            "som_week_id": week.id,
            "som_worked_week_id": worked_week.id,
            "oproject_entry_id": entry_id,
            "oproject_source_data": source_data,
        }

    @api.model
    def _import_openproject_source_entries(self, source_entries):
        """Create immutable timesheets from normalized OpenProject entries."""
        stats = {"created": 0, "duplicates": 0, "skipped": 0}
        seen_entry_ids = set()
        for source_data in source_entries:
            entry_id = source_data.get("openproject_time_entry_id")
            if not isinstance(entry_id, int) or entry_id <= 0:
                _logger.warning("OpenProject entry skipped: invalid entry ID %r.", entry_id)
                stats["skipped"] += 1
                continue
            if entry_id in seen_entry_ids or self.with_context(active_test=False).search_count(
                [("oproject_entry_id", "=", entry_id)]
            ):
                _logger.info("OpenProject entry %s skipped: already imported.", entry_id)
                stats["duplicates"] += 1
                seen_entry_ids.add(entry_id)
                continue
            seen_entry_ids.add(entry_id)
            values = self._prepare_openproject_timesheet_values(source_data)
            if not values:
                stats["skipped"] += 1
                continue
            try:
                with self.env.cr.savepoint():
                    self.create(values)
            except UserError as error:
                _logger.warning(
                    "OpenProject entry %s skipped: %s", entry_id, error
                )
                stats["skipped"] += 1
            except Exception:
                _logger.exception("OpenProject entry %s could not be imported.", entry_id)
                stats["skipped"] += 1
            else:
                stats["created"] += 1
        return stats

    @api.model
    def _import_openproject_timesheets(self, date_from, date_to):
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        client = self._get_openproject_client()
        if not client:
            return {"created": 0, "duplicates": 0, "skipped": 0}

        _logger.info(
            "Starting OpenProject timesheet import from %s to %s.",
            date_from,
            date_to,
        )
        source_entries = []
        read_count = 0
        normalization_skipped = 0
        caches = {"users": {}, "projects": {}, "work_packages": {}}
        try:
            for entry in self._get_openproject_time_entries(client, date_from, date_to):
                read_count += 1
                try:
                    source_entries.append(
                        self._normalize_openproject_entry(client, entry, caches)
                    )
                except (ValueError, KeyError):
                    _logger.exception(
                        "OpenProject entry %s could not be normalized.",
                        entry.get("id"),
                    )
                    normalization_skipped += 1
        except requests.RequestException:
            _logger.exception("OpenProject timesheet import failed while reading the API.")
            raise

        stats = self._import_openproject_source_entries(source_entries)
        stats["skipped"] += normalization_skipped
        _logger.info(
            "OpenProject timesheet import finished: %s read, %s created, "
            "%s duplicates, %s skipped.",
            read_count,
            stats["created"],
            stats["duplicates"],
            stats["skipped"],
        )
        return stats

    @api.model
    def _cron_import_openproject_timesheets(self):
        execution_date = fields.Date.today()
        date_from, date_to = self._get_openproject_week_range(execution_date)
        return self._import_openproject_timesheets(date_from, date_to)
