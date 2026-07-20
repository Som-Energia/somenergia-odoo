"""Load the local OpenProject connection settings."""

from configparser import ConfigParser
from pathlib import Path
from urllib.parse import urlparse


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
    if api_url[:1] == api_url[-1:] and api_url[:1] in ("'", '"'):
        api_url = api_url[1:-1].strip()
    if api_key[:1] == api_key[-1:] and api_key[:1] in ("'", '"'):
        api_key = api_key[1:-1].strip()
    if not api_url or not api_key:
        raise RuntimeError("api_url and api_key must not be empty.")
    parsed_url = urlparse(api_url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise RuntimeError("api_url must be a valid HTTP(S) URL.")
    return api_url, api_key
