import xml.etree.ElementTree as ET
from http import client

from davish.types import Context, WSGIResponse
from davish.utils import utils_app, utils_http, utils_xml


def xml_delete(path: str) -> ET.Element:
    """Read and answer DELETE requests.
    Read rfc4918-9.6 for info.
    """

    multistatus = ET.Element(utils_xml.make_clark("D:multistatus"))
    response = ET.Element(utils_xml.make_clark("D:response"))
    multistatus.append(response)

    href_element = ET.Element(utils_xml.make_clark("D:href"))
    href_element.text = utils_xml.make_href(path)
    response.append(href_element)

    status = ET.Element(utils_xml.make_clark("D:status"))
    status.text = utils_xml.make_response(200)
    response.append(status)

    return multistatus


def do_DELETE(
    context: Context,
    path: str,
) -> WSGIResponse:
    item = context.storage.item_get_from_path(path)
    if not item:
        return utils_http.NOT_FOUND

    item_etag = context.storage.item_etag(item)

    if_match = context.env.get("HTTP_IF_MATCH", "*")
    if if_match not in ("*", item_etag):
        # ETag precondition not verified, do not delete item
        return utils_http.PRECONDITION_FAILED

    context.storage.item_delete(item)
    xml_answer = xml_delete(path)

    headers = {"Content-Type": "text/xml; charset=utf-8"}
    return client.OK, headers, utils_app.xml_response(xml_answer)
