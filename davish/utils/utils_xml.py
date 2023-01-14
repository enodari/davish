import xml.etree.ElementTree as ET
from http import client
from typing import TYPE_CHECKING, Mapping
from urllib.parse import quote

from davish.utils import utils_path

if TYPE_CHECKING:
    from davish.storage import Item

MIMETYPES: Mapping[str, str] = {
    "VADDRESSBOOK": "text/vcard",
    "VCALENDAR": "text/calendar",
}

OBJECT_MIMETYPES: Mapping[str, str] = {
    "VCARD": "text/vcard",
    "VLIST": "text/x-vlist",
    "VCALENDAR": "text/calendar",
}

NAMESPACES: Mapping[str, str] = {
    "C": "urn:ietf:params:xml:ns:caldav",
    "CR": "urn:ietf:params:xml:ns:carddav",
    "D": "DAV:",
    "CS": "http://calendarserver.org/ns/",
    "ICAL": "http://apple.com/ns/ical/",
    "ME": "http://me.com/_namespace/",
}

NAMESPACES_REV: Mapping[str, str] = {v: k for k, v in NAMESPACES.items()}

for short, url in NAMESPACES.items():
    ET.register_namespace("" if short == "D" else short, url)


def make_clark(human_tag: str) -> str:
    """Get XML Clark notation from human tag ``human_tag``.

    If ``human_tag`` is already in XML Clark notation it is returned as-is.

    """
    if human_tag.startswith("{"):
        ns, tag = human_tag[len("{") :].split("}", maxsplit=1)
        if not ns or not tag:
            raise ValueError("Invalid XML tag: %r" % human_tag)
        return human_tag
    ns_prefix, tag = human_tag.split(":", maxsplit=1)
    if not ns_prefix or not tag:
        raise ValueError("Invalid XML tag: %r" % human_tag)
    ns = NAMESPACES.get(ns_prefix, "")
    if not ns:
        raise ValueError("Unknown XML namespace prefix: %r" % human_tag)
    return "{%s}%s" % (ns, tag)


def make_human_tag(clark_tag: str) -> str:
    """Replace known namespaces in XML Clark notation ``clark_tag`` with
       prefix.

    If the namespace is not in ``NAMESPACES`` the tag is returned as-is.

    """
    if not clark_tag.startswith("{"):
        ns_prefix, tag = clark_tag.split(":", maxsplit=1)
        if not ns_prefix or not tag:
            raise ValueError("Invalid XML tag: %r" % clark_tag)
        if ns_prefix not in NAMESPACES:
            raise ValueError("Unknown XML namespace prefix: %r" % clark_tag)
        return clark_tag
    ns, tag = clark_tag[len("{") :].split("}", maxsplit=1)
    if not ns or not tag:
        raise ValueError("Invalid XML tag: %r" % clark_tag)
    ns_prefix = NAMESPACES_REV.get(ns, "")
    if ns_prefix:
        return "%s:%s" % (ns_prefix, tag)
    return clark_tag


def make_response(code: int) -> str:
    """Return full W3C names from HTTP status codes."""
    return "HTTP/1.1 %i %s" % (code, client.responses[code])


def make_href(href: str) -> str:
    """Return prefixed href."""
    assert href == utils_path.sanitize_path(href)
    return quote(href)


def webdav_error(human_tag: str) -> ET.Element:
    """Generate XML error message."""
    root = ET.Element(make_clark("D:error"))
    root.append(ET.Element(make_clark(human_tag)))
    return root


def get_content_type(item: "Item", encoding: str) -> str:
    """Get the content-type of an item with charset and component parameters."""
    mimetype = OBJECT_MIMETYPES[item.tag.value]
    tag = item.tag
    content_type = "%s;charset=%s" % (mimetype, encoding)
    if tag:
        content_type += ";component=%s" % tag
    return content_type
