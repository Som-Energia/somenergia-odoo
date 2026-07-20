#!/usr/bin/env python3
"""Export OpenProject time entries with the data needed for Odoo matching.

Example:
    OPENPROJECT_API_KEY=... python get_time_entries_for_odoo.py
"""

import argparse
import json
import os
from urllib.parse import urljoin

import requests


DEFAULT_BASE_URL = "https://somenergia.openproject.com/api/v3"
DEFAULT_DATE_FROM = "2026-07-13"


class OpenProjectClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.auth = ("apikey", api_key)
        self.session.headers.update({"Accept": "application/hal+json"})

    def get(self, path_or_url, params=None):
        url = urljoin(self.base_url, path_or_url)
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()


def link_id(link):
    """Return the resource ID from an OpenProject HAL link."""
    if not link:
        return None
    return int(link["href"].rstrip("/").rsplit("/", 1)[-1])


def link_title(link):
    return link.get("title") if link else None


def custom_field_value(project, field_key):
    """Project list fields may be represented as a value or a HAL link."""
    value = project.get(field_key)
    if value is not None:
        return value

    link = project.get("_links", {}).get(field_key)
    if isinstance(link, dict):
        return link_title(link)
    return link


def get_custom_field_key(client, field_name):
    schema = client.get("projects/schema")
    field_keys = [
        key
        for key, definition in schema.items()
        if key.startswith("customField")
        and isinstance(definition, dict)
        and definition.get("name") == field_name
    ]
    if len(field_keys) != 1:
        raise RuntimeError(
            "Expected exactly one project custom field named %r; found %s."
            % (field_name, field_keys)
        )
    return field_keys[0]


def get_time_entries(client, date_from, page_size):
    filters = [{"spent_on": {"operator": ">=", "values": [date_from]}}]
    page = client.get(
        "time_entries",
        params={"pageSize": page_size, "filters": json.dumps(filters)},
    )
    while True:
        for entry in page.get("_embedded", {}).get("elements", []):
            # Keep the date guard even when the server-side filter is applied.
            if entry["spentOn"] >= date_from:
                yield entry

        next_page = page.get("_links", {}).get("nextByOffset")
        if not next_page:
            return
        page = client.get(next_page["href"])


def export_time_entries(client, date_from, page_size, ceco_field_name):
    ceco_field_key = get_custom_field_key(client, ceco_field_name)
    users = {}
    projects = {}
    exported_entries = []

    for entry in get_time_entries(client, date_from, page_size):
        links = entry["_links"]
        user_link = links.get("user")
        project_link = links.get("project")
        work_package_link = links.get("workPackage") or links.get("entity")

        user_id = link_id(user_link)
        project_id = link_id(project_link)
        if user_id not in users:
            users[user_id] = client.get(user_link["href"])
        if project_id not in projects:
            projects[project_id] = client.get(project_link["href"])

        user = users[user_id]
        project = projects[project_id]
        exported_entries.append({
            "openproject_time_entry_id": entry["id"],
            "date": entry["spentOn"],
            "hours": entry["hours"],
            "comment": entry.get("comment", {}).get("raw"),
            "openproject_user_id": user_id,
            "employee_work_email": user.get("email"),
            "openproject_project_id": project_id,
            "openproject_project_name": project.get("name"),
            "ceco": custom_field_value(project, ceco_field_key),
            "openproject_work_package_id": link_id(work_package_link),
            "openproject_work_package_subject": link_title(work_package_link),
        })

    return exported_entries


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENPROJECT_URL", DEFAULT_BASE_URL),
        help="OpenProject API v3 base URL",
    )
    parser.add_argument("--date-from", default=DEFAULT_DATE_FROM, help="YYYY-MM-DD")
    parser.add_argument("--page-size", type=int, default=200)
    parser.add_argument("--ceco-field", default="CeCo")
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    api_key = os.environ.get("OPENPROJECT_API_KEY")
    if not api_key:
        raise SystemExit("OPENPROJECT_API_KEY must be set.")
    if arguments.page_size < 1:
        raise SystemExit("--page-size must be greater than zero.")

    client = OpenProjectClient(arguments.base_url, api_key)
    entries = export_time_entries(
        client,
        arguments.date_from,
        arguments.page_size,
        arguments.ceco_field,
    )
    print(json.dumps(entries, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
