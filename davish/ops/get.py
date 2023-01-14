from http import client
from urllib.parse import quote

from davish.storage import Collection, Item
from davish.types import Context, WSGIResponse
from davish.utils import utils_http, utils_xml


def propose_filename(collection: Collection) -> str:
    """Propose a filename for a collection."""
    if collection.is_address_book:
        suffix = "vcf"
    elif collection.is_calendar:
        suffix = "ics"
    else:
        suffix = ""

    return f"{collection.slug}.{suffix}"


def _content_disposition_attachement(filename: str) -> str:
    value = "attachement"
    try:
        encoded_filename = quote(filename, encoding="utf-8")
    except UnicodeEncodeError:
        encoded_filename = ""
    if encoded_filename:
        value += "; filename*=%s''%s" % ("utf-8", encoded_filename)
    return value


def do_GET(
    context: Context,
    path: str,
) -> WSGIResponse:
    item_or_collection = context.storage.get(path)
    if not item_or_collection:
        return utils_http.NOT_FOUND

    if isinstance(item_or_collection, Collection):
        collection = item_or_collection
        if not collection.tag:
            return utils_http.DIRECTORY_LISTING
        content_type = utils_xml.MIMETYPES[collection.tag.value]
        content_disposition = _content_disposition_attachement(
            propose_filename(collection)
        )
        etag = context.storage.collection_etag(collection)
    elif isinstance(item_or_collection, Item):
        item = item_or_collection
        content_type = utils_xml.OBJECT_MIMETYPES[item.tag.value]
        content_disposition = ""
        etag = context.storage.item_etag(item)
    else:
        return utils_http.BAD_REQUEST

    headers = {
        "Content-Type": content_type,
        "Last-Modified": context.storage.get_last_modified(item_or_collection),
        "ETag": etag,
    }

    if content_disposition:
        headers["Content-Disposition"] = content_disposition

    answer = context.storage.serialize(item_or_collection)
    return client.OK, headers, answer
