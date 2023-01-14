from http import client

from davish.types import Context, WSGIResponse
from davish.utils import utils_http

ALLOWED_METHODS = ["DELETE", "GET", "HEAD", "OPTIONS", "PROPFIND", "PUT", "REPORT"]


def do_OPTIONS(
    context: Context,
    path: str,
) -> WSGIResponse:
    """Manage OPTIONS request."""
    headers = {
        "Allow": ", ".join(ALLOWED_METHODS),
        "DAV": utils_http.DAV_HEADERS,
    }
    return client.OK, headers, None
