from .delete import do_DELETE
from .get import do_GET
from .head import do_HEAD
from .options import do_OPTIONS
from .propfind import do_PROPFIND
from .put import do_PUT
from .report import do_REPORT

METHODS_MAP = {
    "DELETE": do_DELETE,
    "GET": do_GET,
    "HEAD": do_HEAD,
    "OPTIONS": do_OPTIONS,
    "PROPFIND": do_PROPFIND,
    "PUT": do_PUT,
    "REPORT": do_REPORT,
}
