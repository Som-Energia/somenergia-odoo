"""Load the local OpenProject connection settings."""

from configparser import ConfigParser
from pathlib import Path
from urllib.parse import urljoin, urlparse


CONFIG_PATH = Path(__file__).with_name(".openproject.conf")


def _origin(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
        raise RuntimeError("OpenProject URL must be a valid HTTP(S) URL.")
    port = parsed_url.port
    if port is None:
        port = 443 if parsed_url.scheme == "https" else 80
    return parsed_url.scheme.lower(), parsed_url.hostname.lower(), port


def resolve_openproject_url(base_url, path_or_url):
    """Resolve a HAL URL and reject a change of authenticated origin."""
    url = urljoin(base_url.rstrip("/") + "/", path_or_url)
    if _origin(url) != _origin(base_url):
        raise RuntimeError("OpenProject URL points outside the configured origin.")
    return url


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
    _origin(api_url)
    return api_url, api_key
