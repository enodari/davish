from davish.ops.get import do_GET
from davish.types import Context, WSGIResponse


def do_HEAD(
    context: Context,
    path: str,
) -> WSGIResponse:
    """Manage HEAD request."""
    # Body is dropped in `Application.__call__` for HEAD requests
    return do_GET(context, path)
