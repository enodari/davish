import io
import xml.etree.ElementTree as ET
from typing import Optional

from davish import types
from davish.utils import utils_http


def read_xml_request_body(environ: types.WSGIEnviron) -> Optional[ET.Element]:
    content = utils_http.decode_request(
        environ,
        utils_http.read_raw_request_body(environ),
    )
    if not content:
        return None
    try:
        xml_content = ET.fromstring(content)
    except ET.ParseError as e:
        raise RuntimeError("Failed to parse XML: %s" % e) from e
    return xml_content


def xml_response(xml_content: ET.Element) -> bytes:
    f = io.BytesIO()
    ET.ElementTree(xml_content).write(f, encoding="utf-8", xml_declaration=True)
    return f.getvalue()
