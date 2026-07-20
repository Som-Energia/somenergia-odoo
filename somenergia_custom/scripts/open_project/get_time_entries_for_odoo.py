#!/usr/bin/env python3
"""Export OpenProject time entries with the data needed for Odoo matching.

Example:
    python get_time_entries_for_odoo.py
"""

import argparse
import json
from datetime import date
from urllib.parse import urljoin

import requests

from openproject_config import load_openproject_config


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


def get_time_entries(client, date_from, page_size):
    date_to = date.today().isoformat()
    filters = [{
        "spent_on": {
            "operator": "<>d",
            "values": [date_from, date_to],
        },
    }]
    page = client.get(
        "time_entries",
        params={"pageSize": page_size, "filters": json.dumps(filters)},
    )
    while True:
        for entry in page.get("_embedded", {}).get("elements", []):
            # Keep the date guard even when the server-side filter is applied.
            if date_from <= entry["spentOn"] <= date_to:
                yield entry

        next_page = page.get("_links", {}).get("nextByOffset")
        if not next_page:
            return
        page = client.get(next_page["href"])


def export_time_entries(client, date_from, page_size):
    users = {}
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

        user = users[user_id]
        exported_entries.append({
            "openproject_time_entry_id": entry["id"],
            "date": entry["spentOn"],
            "hours": entry["hours"],
            "comment": entry.get("comment", {}).get("raw"),
            "openproject_user_id": user_id,
            "employee_work_email": user.get("email"),
            "openproject_project_id": project_id,
            "openproject_project_name": link_title(project_link),
            "openproject_work_package_id": link_id(work_package_link),
            "openproject_work_package_subject": link_title(work_package_link),
        })

    return exported_entries


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date-from", default=DEFAULT_DATE_FROM, help="YYYY-MM-DD")
    parser.add_argument("--page-size", type=int, default=200)
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    base_url, api_key = load_openproject_config()
    if arguments.page_size < 1:
        raise SystemExit("--page-size must be greater than zero.")

    client = OpenProjectClient(base_url, api_key)
    entries = export_time_entries(
        client,
        arguments.date_from,
        arguments.page_size,
    )
    print(json.dumps(entries, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
