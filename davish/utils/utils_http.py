import contextlib
from http import client

from davish import types

NOT_ALLOWED: types.WSGIResponse = (
    client.FORBIDDEN,
    {"Content-Type": "text/plain"},
    "Access to the requested resource forbidden.",
)
FORBIDDEN: types.WSGIResponse = (
    client.FORBIDDEN,
    {"Content-Type": "text/plain"},
    "Action on the requested resource refused.",
)
BAD_REQUEST: types.WSGIResponse = (
    client.BAD_REQUEST,
    {"Content-Type": "text/plain"},
    "Bad Request",
)
NOT_FOUND: types.WSGIResponse = (
    client.NOT_FOUND,
    {"Content-Type": "text/plain"},
    "The requested resource could not be found.",
)
CONFLICT: types.WSGIResponse = (
    client.CONFLICT,
    {"Content-Type": "text/plain"},
    "Conflict in the request.",
)
METHOD_NOT_ALLOWED: types.WSGIResponse = (
    client.METHOD_NOT_ALLOWED,
    {"Content-Type": "text/plain"},
    "The method is not allowed on the requested resource.",
)
PRECONDITION_FAILED: types.WSGIResponse = (
    client.PRECONDITION_FAILED,
    {"Content-Type": "text/plain"},
    "Precondition failed.",
)
REQUEST_TIMEOUT: types.WSGIResponse = (
    client.REQUEST_TIMEOUT,
    {"Content-Type": "text/plain"},
    "Connection timed out.",
)
DIRECTORY_LISTING: types.WSGIResponse = (
    client.FORBIDDEN,
    {"Content-Type": "text/plain"},
    "Directory listings are not supported.",
)

# TODO: maybe this header should reflect what the library really does
DAV_HEADERS: str = "1, 2, 3, calendar-access, addressbook, extended-mkcol"


def decode_request(environ: types.WSGIEnviron, text: bytes) -> str:
    """Try to magically decode ``text`` according to given ``environ``."""
    # List of charsets to try
    charsets: list[str] = []

    # First append content charset given in the request
    content_type = environ.get("CONTENT_TYPE")
    if content_type and "charset=" in content_type:
        charsets.append(content_type.split("charset=")[1].split(";")[0].strip())
    # Then append various fallbacks
    charsets.append("utf-8")
    charsets.append("iso8859-1")
    # Remove duplicates
    for i, s in reversed(list(enumerate(charsets))):
        if s in charsets[:i]:
            del charsets[i]

    # Try to decode
    for charset in charsets:
        with contextlib.suppress(UnicodeDecodeError):
            return text.decode(charset)
    raise UnicodeDecodeError(
        "decode_request",
        text,
        0,
        len(text),
        "all codecs failed [%s]" % ", ".join(charsets),
    )


def read_raw_request_body(environ: types.WSGIEnviron) -> bytes:
    content_length = int(environ.get("CONTENT_LENGTH") or 0)
    if not content_length:
        return b""
    content = environ["wsgi.input"].read(content_length)
    if len(content) < content_length:
        raise RuntimeError("Request body too short: %d" % len(content))
    return content


def read_request_body(environ: types.WSGIEnviron) -> str:
    return decode_request(environ, read_raw_request_body(environ))
