import posixpath
import socket
import xml.etree.ElementTree as ET
from http import client
from typing import Iterable, Iterator, Optional, Sequence, Tuple
from urllib.parse import unquote, urlparse

from davish.storage import Collection, Item
from davish.types import Context, WSGIResponse
from davish.utils import utils_app, utils_http, utils_path, utils_xml


def xml_report(
    context: Context,
    path: str,
    xml_request: Optional[ET.Element],
    collection: Collection,
) -> Tuple[int, ET.Element]:
    """Read and answer REPORT requests.

    Read rfc3253-3.6 for info.

    """
    multistatus = ET.Element(utils_xml.make_clark("D:multistatus"))
    if xml_request is None:
        return client.MULTI_STATUS, multistatus
    root = xml_request
    if root.tag in (
        utils_xml.make_clark("D:principal-search-property-set"),
        utils_xml.make_clark("D:principal-property-search"),
        utils_xml.make_clark("D:expand-property"),
    ):
        # We don't support searching for principals or indirect retrieving of
        # properties, just return an empty result.
        # InfCloud asks for expand-property reports (even if we don't announce
        # support for them) and stops working if an error code is returned.
        return client.MULTI_STATUS, multistatus
    if (
        root.tag == utils_xml.make_clark("C:calendar-multiget")
        and not collection.is_calendar
        or root.tag == utils_xml.make_clark("CR:addressbook-multiget")
        and not collection.is_address_book
        or root.tag == utils_xml.make_clark("D:sync-collection")
        and collection.tag not in ("VADDRESSBOOK", "VCALENDAR")
    ):
        return client.FORBIDDEN, utils_xml.webdav_error("D:supported-report")
    prop_element = root.find(utils_xml.make_clark("D:prop"))
    props = [prop.tag for prop in prop_element] if prop_element is not None else []

    hreferences: Iterable[str]
    if root.tag in (
        utils_xml.make_clark("C:calendar-multiget"),
        utils_xml.make_clark("CR:addressbook-multiget"),
    ):
        # Read rfc4791-7.9 for info
        hreferences = set()
        for href_element in root.findall(utils_xml.make_clark("D:href")):
            temp_url_path = urlparse(href_element.text).path
            assert isinstance(temp_url_path, str)
            href_path = utils_path.sanitize_path(unquote(temp_url_path))
            if (href_path + "/").startswith("/"):
                hreferences.add(href_path)

    else:
        hreferences = (path,)

    # Retrieve everything required for finishing the request.
    retrieved_items = list(
        retrieve_items(context, collection, hreferences, multistatus)
    )

    while retrieved_items:
        item = retrieved_items.pop(0)

        found_props = []
        not_found_props = []

        for tag in props:
            element = ET.Element(tag)
            if tag == utils_xml.make_clark("D:getetag"):
                element.text = context.storage.item_etag(item)
                found_props.append(element)
            elif tag == utils_xml.make_clark("D:getcontenttype"):
                element.text = utils_xml.get_content_type(item, "utf-8")
                found_props.append(element)
            elif tag in (
                utils_xml.make_clark("C:calendar-data"),
                utils_xml.make_clark("CR:address-data"),
            ):
                element.text = context.storage.item_serialize(item)
                found_props.append(element)
            else:
                not_found_props.append(element)

        assert item.href
        uri = utils_path.unstrip_path(posixpath.join(collection.slug, item.href))
        multistatus.append(
            xml_item_response(
                uri,
                found_props=found_props,
                not_found_props=not_found_props,
                found_item=True,
            )
        )

    return client.MULTI_STATUS, multistatus


def xml_item_response(
    href: str,
    found_props: Sequence[ET.Element] = (),
    not_found_props: Sequence[ET.Element] = (),
    found_item: bool = True,
) -> ET.Element:
    response = ET.Element(utils_xml.make_clark("D:response"))

    href_element = ET.Element(utils_xml.make_clark("D:href"))
    href_element.text = utils_xml.make_href(href)
    response.append(href_element)

    if found_item:
        for code, props in ((200, found_props), (404, not_found_props)):
            if props:
                propstat = ET.Element(utils_xml.make_clark("D:propstat"))
                status = ET.Element(utils_xml.make_clark("D:status"))
                status.text = utils_xml.make_response(code)
                prop_element = ET.Element(utils_xml.make_clark("D:prop"))
                for prop in props:
                    prop_element.append(prop)
                propstat.append(prop_element)
                propstat.append(status)
                response.append(propstat)
    else:
        status = ET.Element(utils_xml.make_clark("D:status"))
        status.text = utils_xml.make_response(404)
        response.append(status)

    return response


def retrieve_items(
    context: Context,
    collection: Collection,
    hreferences: Iterable[str],
    multistatus: ET.Element,
) -> Iterator[Item]:
    """Retrieves all items that are referenced in ``hreferences`` from
    ``collection`` and adds 404 responses for missing and invalid items
    to ``multistatus``."""
    collection_requested = False

    """Extracts all names from references in ``hreferences`` and adds
    404 responses for invalid references to ``multistatus``.
    If the whole collections is referenced ``collection_requested``
    gets set to ``True``."""
    hreference_names = []

    for hreference in hreferences:
        try:
            # name = utils_path.name_from_path(hreference, collection.slug)
            collection_path, item_href = context.storage.split_path(hreference)
            if collection_path != collection.slug:
                raise ValueError()
        except ValueError:
            response = xml_item_response(hreference, found_item=False)
            multistatus.append(response)
            continue
        if item_href:
            # Reference is an item
            hreference_names.append(item_href)
        else:
            # Reference is a collection
            collection_requested = True

    collection_items = context.storage.collection_items(collection)
    items_hrefs = {i.href: i for i in collection_items}
    for href in hreference_names:
        item = items_hrefs.get(href, None)
        if not item:
            uri = utils_path.unstrip_path(posixpath.join(collection.slug, href))
            response = xml_item_response(uri, found_item=False)
            multistatus.append(response)
        else:
            yield item

    if collection_requested:
        for item in collection_items:
            yield item


def do_REPORT(
    context: Context,
    path: str,
) -> WSGIResponse:
    try:
        xml_content = utils_app.read_xml_request_body(context.env)
    except RuntimeError:
        return utils_http.BAD_REQUEST
    except socket.timeout:
        return utils_http.REQUEST_TIMEOUT

    item = context.storage.get(path)
    if not item:
        return utils_http.NOT_FOUND

    if isinstance(item, Collection):
        collection = item
    else:
        assert item.collection is not None
        collection = item.collection

    try:
        status, xml_answer = xml_report(
            context,
            path,
            xml_content,
            collection,
        )
    except ValueError:
        return utils_http.BAD_REQUEST

    headers = {"Content-Type": "text/xml; charset=utf-8"}
    return status, headers, utils_app.xml_response(xml_answer)
