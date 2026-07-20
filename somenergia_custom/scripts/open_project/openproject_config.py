"""Load the local OpenProject connection settings."""

from configparser import ConfigParser
from pathlib import Path


CONFIG_PATH = Path(__file__).with_name(".openproject.conf")


def load_openproject_config():
    config = ConfigParser()
    if not config.read(CONFIG_PATH):
        raise RuntimeError(
            "OpenProject configuration file not found: %s" % CONFIG_PATH
        )

    try:
        api_url = config["openproject"]["api_url"].strip()
        api_key = config["openproject"]["api_key"].strip()
    except KeyError as error:
        raise RuntimeError(
            "The [openproject] section must define api_url and api_key."
        ) from error
    if not api_url or not api_key:
        raise RuntimeError("api_url and api_key must not be empty.")
    return api_url, api_key
