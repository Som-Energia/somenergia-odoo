#!/usr/bin/env python3
"""Inspect OpenProject project custom-field definitions and current values.

Example:
    OPENPROJECT_API_KEY=... python get_project_custom_fields.py
"""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urljoin

import requests


DEFAULT_BASE_URL = "https://somenergia.openproject.com/api/v3"
DEFAULT_OUTPUT = Path(__file__).with_name("project_custom_fields.json")


def get(client, base_url, path_or_url, params=None):
    url = urljoin(base_url.rstrip("/") + "/", path_or_url)
    response = client.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def get_custom_fields(resource):
    fields = {
        key: value
        for key, value in resource.items()
        if key.startswith("customField")
    }
    fields.update({
        key: value
        for key, value in resource.get("_links", {}).items()
        if key.startswith("customField")
    })
    return fields


def get_projects(client, base_url, page_size):
    page = get(client, base_url, "projects", params={"pageSize": page_size})
    while True:
        yield from page.get("_embedded", {}).get("elements", [])
        next_page = page.get("_links", {}).get("nextByOffset")
        if not next_page:
            return
        page = get(client, base_url, next_page["href"])


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENPROJECT_URL", DEFAULT_BASE_URL),
        help="OpenProject API v3 base URL",
    )
    parser.add_argument("--page-size", type=int, default=200)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="JSON output file (default: %(default)s)",
    )
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    api_key = os.environ.get("OPENPROJECT_API_KEY")
    if not api_key:
        raise SystemExit("OPENPROJECT_API_KEY must be set.")
    if arguments.page_size < 1:
        raise SystemExit("--page-size must be greater than zero.")

    client = requests.Session()
    client.auth = ("apikey", api_key)
    client.headers.update({"Accept": "application/hal+json"})

    schema = get(client, arguments.base_url, "projects/schema")
    projects = []
    for project_link in get_projects(client, arguments.base_url, arguments.page_size):
        project = get(client, arguments.base_url, project_link["_links"]["self"]["href"])
        projects.append({
            "id": project["id"],
            "identifier": project["identifier"],
            "name": project["name"],
            "custom_fields": get_custom_fields(project),
        })

    result = {
        "schema_custom_fields": get_custom_fields(schema),
        "schema_attribute_groups": schema.get("_attributeGroups", []),
        "projects": projects,
    }
    arguments.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("JSON written to %s" % arguments.output)


if __name__ == "__main__":
    main()
