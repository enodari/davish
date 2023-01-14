from davish.ops import METHODS_MAP
from davish.storage import BaseStorage
from davish.types import Context, WSGIEnviron
from davish.utils import utils_http, utils_path

ALLOWED_METHODS = METHODS_MAP.keys()


def handle_dav_request(
    environ: WSGIEnviron,
    storage: BaseStorage,
) -> tuple[int, dict[str, str], bytes]:
    request_method = environ["REQUEST_METHOD"].upper()
    unsafe_path = environ.get("PATH_INFO", "")

    path = utils_path.sanitize_path(unsafe_path)

    function = METHODS_MAP.get(request_method, None)
    if not function:
        status, headers, content = utils_http.METHOD_NOT_ALLOWED
    else:
        status, headers, content = function(
            Context(
                env=environ,
                storage=storage,
            ),
            path,
        )

    if isinstance(content, str):
        headers["Content-Type"] += "; charset=utf-8"
        content = content.encode("utf-8")

    return status, headers, content or b""
