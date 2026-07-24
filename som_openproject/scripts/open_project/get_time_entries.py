import requests
import json

from openproject_config import load_openproject_config

USERNAME = "apikey"

DATE_FROM = "2026-01-14"
DATE_TO = "2026-01-15"
PAGE_SIZE = 5


def get_time_entries():
    base_url, api_key = load_openproject_config()

    results = []
    offset = 1

    response = requests.get(
        f"{base_url.rstrip('/')}/time_entries",
        auth=(USERNAME, api_key),
        headers={"Accept": "application/json"},
        params={
            "pageSize": PAGE_SIZE,
            "offset": offset
        }
    )

    response.raise_for_status()
    data = response.json()

    elements = data.get("_embedded", {}).get("elements", [])
    if not elements:
        return {}

    for entry in elements:
        results.append({
            "date": entry["spentOn"],
            "user": entry["_links"]["user"]["title"],
            "task": (
                entry["_links"]["workPackage"]["title"]
                if "workPackage" in entry["_links"]
                else None
            ),
            "project": entry["_links"]["project"]["title"],
            "hours": entry["hours"]
        })

    offset += 1

    return results


if __name__ == "__main__":
    time_entries = get_time_entries()
    print(json.dumps(time_entries, indent=2, ensure_ascii=False))
