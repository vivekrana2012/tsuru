"""RSS feed route handler"""
from fastapi import Request
from fastapi.responses import Response

from routes.utils import generate_rss_xml, get_base_path


async def rss_feed(request: Request):
    """Serve RSS XML feed"""
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    base_path = get_base_path(request)
    xml_content = generate_rss_xml(base_url, base_path)
    return Response(content=xml_content, media_type="application/rss+xml; charset=utf-8")
