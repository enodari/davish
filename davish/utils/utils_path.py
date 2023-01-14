import posixpath


def strip_path(path: str) -> str:
    assert sanitize_path(path) == path
    return path.strip("/")


def unstrip_path(stripped_path: str, trailing_slash: bool = False) -> str:
    assert strip_path(sanitize_path(stripped_path)) == stripped_path
    assert stripped_path or trailing_slash
    path = "/%s" % stripped_path
    if trailing_slash and not path.endswith("/"):
        path += "/"
    return path


def sanitize_path(path: str) -> str:
    """Make path absolute with leading slash to prevent access to other data.

    Preserve potential trailing slash.

    """
    trailing_slash = "/" if path.endswith("/") else ""
    path = posixpath.normpath(path)
    new_path = "/"
    for part in path.split("/"):
        if not is_safe_path_component(part):
            continue
        new_path = posixpath.join(new_path, part)
    trailing_slash = "" if new_path.endswith("/") else trailing_slash
    return new_path + trailing_slash


def is_safe_path_component(path: str) -> bool:
    """Check if path is a single component of a path.

    Check that the path is safe to join too.

    """
    return bool(path) and "/" not in path and path not in (".", "..")
