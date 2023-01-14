import socket
from http import client
from typing import Mapping

from davish.types import Context, WSGIResponse
from davish.utils import utils_http, utils_xml

MIMETYPE_TAGS: Mapping[str, str] = {
    value: key for key, value in utils_xml.MIMETYPES.items()
}


def do_PUT(
    context: Context,
    path: str,
) -> WSGIResponse:
    try:
        content = utils_http.read_request_body(context.env)
    except RuntimeError:
        return utils_http.BAD_REQUEST
    except socket.timeout:
        return utils_http.REQUEST_TIMEOUT

    collection_slug, item_href = context.storage.split_path(path)
    collection = context.storage.collection_get(collection_slug)
    if not collection or not item_href:
        return utils_http.CONFLICT

    maybe_item = context.storage.item_get(item_href, collection)

    etag = context.env.get("HTTP_IF_MATCH", "")

    if not maybe_item and etag:
        # Etag asked but no item found: item has been removed
        return utils_http.PRECONDITION_FAILED

    if maybe_item and etag and context.storage.item_etag(maybe_item) != etag:
        # Etag asked but item not matching: item has changed
        return utils_http.PRECONDITION_FAILED

    match = context.env.get("HTTP_IF_NONE_MATCH", "") == "*"
    if maybe_item and match:
        # Creation asked but item found: item can't be replaced
        return utils_http.PRECONDITION_FAILED

    try:
        uploaded_item = context.storage.item_upload(
            item_href,
            maybe_item,
            collection,
            content,
        )
    except Exception:
        return utils_http.BAD_REQUEST

    if not uploaded_item:
        return utils_http.BAD_REQUEST

    headers = {"ETag": context.storage.item_etag(uploaded_item)}
    return client.CREATED, headers, None
