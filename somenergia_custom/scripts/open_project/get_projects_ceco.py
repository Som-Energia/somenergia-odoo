#!/usr/bin/env python3
"""List OpenProject projects and their current CeCo custom-field value.

Example:
    python get_projects_ceco.py
"""

import argparse
import json
from urllib.parse import urljoin

import requests

from openproject_config import load_openproject_config


def get(client, base_url, path_or_url, params=None):
    response = client.get(
        urljoin(base_url.rstrip("/") + "/", path_or_url),
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_ceco_field(schema, field_name):
    fields = [
        (key, definition)
        for key, definition in schema.items()
        if key.startswith("customField")
        and isinstance(definition, dict)
        and definition.get("name") == field_name
    ]
    if len(fields) != 1:
        raise RuntimeError(
            "Expected exactly one project custom field named %r; found %s."
            % (field_name, [key for key, _definition in fields])
        )
    return fields[0]


def get_custom_field_value(project, field_key):
    if project.get(field_key) is not None:
        return project[field_key]

    link = project.get("_links", {}).get(field_key)
    return link.get("title") if isinstance(link, dict) else link


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
    parser.add_argument("--ceco-field", default="CeCo")
    parser.add_argument("--page-size", type=int, default=200)
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    base_url, api_key = load_openproject_config()
    if arguments.page_size < 1:
        raise SystemExit("--page-size must be greater than zero.")

    client = requests.Session()
    client.auth = ("apikey", api_key)
    client.headers.update({"Accept": "application/hal+json"})

    ceco_key, ceco_schema = get_ceco_field(
        get(client, base_url, "projects/schema"), arguments.ceco_field
    )
    projects = []
    for project_link in get_projects(client, base_url, arguments.page_size):
        project = get(client, base_url, project_link["_links"]["self"]["href"])
        projects.append({
            "id": project["id"],
            "identifier": project["identifier"],
            "name": project["name"],
            "active": project["active"],
            "ceco": get_custom_field_value(project, ceco_key),
        })

    print(json.dumps({
        "ceco_field_key": ceco_key,
        "ceco_field_schema": ceco_schema,
        "projects": projects,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
