import collections
import posixpath
import socket
import xml.etree.ElementTree as ET
from http import client
from typing import Dict, Iterable, List, Optional, Sequence

from davish.storage import Collection, Item
from davish.types import Context, WSGIResponse
from davish.utils import utils_app, utils_http, utils_path, utils_xml


def xml_propfind(
    context: Context,
    path: str,
    xml_request: Optional[ET.Element],
    items: Iterable[Collection | Item],
    user: str,
) -> Optional[ET.Element]:
    """Read and answer PROPFIND requests.

    Read rfc4918-9.1 for info.

    The collections parameter is a list of collections that are to be included
    in the output.

    """
    # A client may choose not to submit a request body.  An empty PROPFIND
    # request body MUST be treated as if it were an 'allprop' request.
    top_element = (
        xml_request[0]
        if xml_request is not None
        else ET.Element(utils_xml.make_clark("D:allprop"))
    )

    props: List[str] = []
    allprop = False
    propname = False
    if top_element.tag == utils_xml.make_clark("D:allprop"):
        allprop = True
    elif top_element.tag == utils_xml.make_clark("D:propname"):
        propname = True
    elif top_element.tag == utils_xml.make_clark("D:prop"):
        props.extend(prop.tag for prop in top_element)

    # Writing answer
    multistatus = ET.Element(utils_xml.make_clark("D:multistatus"))

    for item in items:
        multistatus.append(
            xml_propfind_response(
                context,
                path,
                item,
                props,
                write=True,
                allprop=allprop,
                propname=propname,
                user=user,
            )
        )

    return multistatus


def xml_propfind_response(
    context: Context,
    path: str,
    item: Collection | Item,
    props: Sequence[str],
    write: bool = False,
    propname: bool = False,
    allprop: bool = False,
    user: str = "",
) -> ET.Element:
    """Build and return a PROPFIND response."""
    if propname and allprop or (props and (propname or allprop)):
        raise ValueError("Only use one of props, propname and allprops")

    if isinstance(item, Collection):
        is_collection = True
        if item.tag:
            is_leaf = item.tag.value in ("VADDRESSBOOK", "VCALENDAR")
        else:
            is_leaf = False
        collection = item
        # Some clients expect collections to end with `/`
        uri = utils_path.unstrip_path(collection.slug, True)
    elif isinstance(item, Item):
        is_collection = is_leaf = False
        assert item.collection is not None
        assert item.href
        collection = item.collection
        uri = utils_path.unstrip_path(posixpath.join(collection.slug, item.href))
    else:
        raise Exception("TODO: should not happen")

    response = ET.Element(utils_xml.make_clark("D:response"))
    href = ET.Element(utils_xml.make_clark("D:href"))
    href.text = utils_xml.make_href(uri)
    response.append(href)

    if propname or allprop:
        props = []
        # Should list all properties that can be retrieved by the code below
        props.append(utils_xml.make_clark("D:principal-collection-set"))
        props.append(utils_xml.make_clark("D:current-user-principal"))
        props.append(utils_xml.make_clark("D:current-user-privilege-set"))
        props.append(utils_xml.make_clark("D:supported-report-set"))
        props.append(utils_xml.make_clark("D:resourcetype"))
        props.append(utils_xml.make_clark("D:owner"))

        if is_collection and collection.is_principal:
            props.append(utils_xml.make_clark("C:calendar-user-address-set"))
            props.append(utils_xml.make_clark("D:principal-URL"))
            props.append(utils_xml.make_clark("CR:addressbook-home-set"))
            props.append(utils_xml.make_clark("C:calendar-home-set"))

        if not is_collection or is_leaf:
            props.append(utils_xml.make_clark("D:getetag"))
            props.append(utils_xml.make_clark("D:getlastmodified"))
            props.append(utils_xml.make_clark("D:getcontenttype"))
            props.append(utils_xml.make_clark("D:getcontentlength"))

        if is_collection:
            if is_leaf:
                props.append(utils_xml.make_clark("D:displayname"))
            if collection.is_calendar:
                props.append(utils_xml.make_clark("CS:getctag"))
                props.append(utils_xml.make_clark("C:supported-calendar-component-set"))

    responses: Dict[int, List[ET.Element]] = collections.defaultdict(list)
    if propname:
        for tag in props:
            responses[200].append(ET.Element(tag))
        props = []
    for tag in props:
        element = ET.Element(tag)
        is404 = False
        if tag == utils_xml.make_clark("D:getetag"):
            if not is_collection or is_leaf:
                if isinstance(item, Collection):
                    element.text = context.storage.collection_etag(item)
                else:
                    element.text = context.storage.item_etag(item)
            else:
                is404 = True
        elif tag == utils_xml.make_clark("D:getlastmodified"):
            if not is_collection or is_leaf:
                element.text = context.storage.get_last_modified(item)
            else:
                is404 = True
        elif tag == utils_xml.make_clark("D:principal-collection-set"):
            child_element = ET.Element(utils_xml.make_clark("D:href"))
            child_element.text = utils_xml.make_href("/")
            element.append(child_element)
        elif (
            tag
            in (
                utils_xml.make_clark("C:calendar-user-address-set"),
                utils_xml.make_clark("D:principal-URL"),
                utils_xml.make_clark("CR:addressbook-home-set"),
                utils_xml.make_clark("C:calendar-home-set"),
            )
            and is_collection
            and collection.is_principal
        ):
            child_element = ET.Element(utils_xml.make_clark("D:href"))
            child_element.text = utils_xml.make_href(path)
            element.append(child_element)
        elif tag == utils_xml.make_clark("C:supported-calendar-component-set"):
            human_tag = utils_xml.make_human_tag(tag)
            if is_collection and is_leaf:
                # TODO: add VEVENT and VJOURNAL support
                # components = ["VTODO", "VEVENT", "VJOURNAL"]
                components = ["VEVENT"]
                for component in components:
                    comp = ET.Element(utils_xml.make_clark("C:comp"))
                    comp.set("name", component)
                    element.append(comp)
            else:
                is404 = True
        elif tag == utils_xml.make_clark("D:current-user-principal"):
            child_element = ET.Element(utils_xml.make_clark("D:href"))
            child_element.text = utils_xml.make_href("/%s/" % user)
            element.append(child_element)
        elif tag == utils_xml.make_clark("D:current-user-privilege-set"):
            privileges = ["D:read"]
            if write:
                privileges.append("D:all")
                privileges.append("D:write")
                privileges.append("D:write-properties")
                privileges.append("D:write-content")
            for human_tag in privileges:
                privilege = ET.Element(utils_xml.make_clark("D:privilege"))
                privilege.append(ET.Element(utils_xml.make_clark(human_tag)))
                element.append(privilege)
        elif tag == utils_xml.make_clark("D:supported-report-set"):
            # These 3 reports are not implemented
            reports = [
                "D:expand-property",
                "D:principal-search-property-set",
                "D:principal-property-search",
            ]
            if is_collection and is_leaf:
                reports.append("D:sync-collection")
                if collection.is_address_book:
                    reports.append("CR:addressbook-multiget")
                    reports.append("CR:addressbook-query")
                elif collection.is_calendar:
                    reports.append("C:calendar-multiget")
                    reports.append("C:calendar-query")
            for human_tag in reports:
                supported_report = ET.Element(
                    utils_xml.make_clark("D:supported-report")
                )
                report_element = ET.Element(utils_xml.make_clark("D:report"))
                report_element.append(ET.Element(utils_xml.make_clark(human_tag)))
                supported_report.append(report_element)
                element.append(supported_report)
        elif tag == utils_xml.make_clark("D:getcontentlength"):
            if not is_collection or is_leaf:
                try:
                    element.text = str(
                        len(context.storage.serialize(item).encode("utf-8"))
                    )
                except Exception:
                    is404 = True
            else:
                is404 = True
        elif tag == utils_xml.make_clark("D:owner"):
            # return empty elment, if no owner available (rfc3744-5.1)
            child_element = ET.Element(utils_xml.make_clark("D:href"))
            child_element.text = utils_xml.make_href("/%s/" % user)
            element.append(child_element)
        elif is_collection:
            if tag == utils_xml.make_clark("D:getcontenttype"):
                if is_leaf and collection.tag:
                    element.text = utils_xml.MIMETYPES[collection.tag.value]
                else:
                    is404 = True
            elif tag == utils_xml.make_clark("D:resourcetype"):
                if collection.is_principal:
                    child_element = ET.Element(utils_xml.make_clark("D:principal"))
                    element.append(child_element)
                if is_leaf:
                    if collection.is_address_book:
                        child_element = ET.Element(
                            utils_xml.make_clark("CR:addressbook")
                        )
                        element.append(child_element)
                    elif collection.is_calendar:
                        child_element = ET.Element(utils_xml.make_clark("C:calendar"))
                        element.append(child_element)
                child_element = ET.Element(utils_xml.make_clark("D:collection"))
                element.append(child_element)
            elif tag == utils_xml.make_clark("D:displayname"):
                displayname = collection.name
                if not displayname and is_leaf:
                    displayname = collection.slug
                if displayname is not None:
                    element.text = displayname
                else:
                    is404 = True
            elif tag == utils_xml.make_clark("CS:getctag"):
                if is_leaf:
                    element.text = context.storage.collection_etag(collection)
                else:
                    is404 = True

        # Not for collections
        elif tag == utils_xml.make_clark("D:getcontenttype"):
            assert not isinstance(item, Collection)
            element.text = utils_xml.get_content_type(item, "utf-8")
        elif tag == utils_xml.make_clark("D:resourcetype"):
            # resourcetype must be returned empty for non-collection elements
            pass
        else:
            is404 = True

        responses[404 if is404 else 200].append(element)

    for status_code, childs in responses.items():
        if not childs:
            continue
        propstat = ET.Element(utils_xml.make_clark("D:propstat"))
        response.append(propstat)
        prop = ET.Element(utils_xml.make_clark("D:prop"))
        prop.extend(childs)
        propstat.append(prop)
        status = ET.Element(utils_xml.make_clark("D:status"))
        status.text = utils_xml.make_response(status_code)
        propstat.append(status)

    return response


def do_PROPFIND(
    context: Context,
    path: str,
) -> WSGIResponse:
    try:
        xml_content = utils_app.read_xml_request_body(context.env)
    except RuntimeError:
        return utils_http.BAD_REQUEST
    except socket.timeout:
        return utils_http.REQUEST_TIMEOUT

    items = context.storage.discover(path, context.env.get("HTTP_DEPTH", "0"))
    if not items:
        return utils_http.NOT_FOUND

    headers = {
        "DAV": utils_http.DAV_HEADERS,
        "Content-Type": "text/xml; charset=utf-8",
    }
    xml_answer = xml_propfind(
        context,
        path,
        xml_content,
        items,
        user=context.storage.user,
    )
    if xml_answer is None:
        return utils_http.NOT_ALLOWED

    return client.MULTI_STATUS, headers, utils_app.xml_response(xml_answer)
