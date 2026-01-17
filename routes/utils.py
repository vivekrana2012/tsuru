"""Shared utilities for routes"""
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from itsdangerous import URLSafeTimedSerializer, BadSignature
from urllib.parse import urlparse, urlunparse
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import httpx
import re
import secrets
import hashlib
import os
from datetime import datetime
from database import get_feed_entries

# Setup
templates = Jinja2Templates(directory="templates")
limiter = Limiter(key_func=get_remote_address)

# CSRF token generator
SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))
csrf_serializer = URLSafeTimedSerializer(SECRET_KEY)

# Load version
with open('VERSION', 'r') as f:
    VERSION = f.read().strip()


def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return csrf_serializer.dumps(secrets.token_urlsafe(32))


def validate_csrf_token(token: str) -> bool:
    """Validate CSRF token (expires after 1 hour)"""
    try:
        csrf_serializer.loads(token, max_age=3600)
        return True
    except (BadSignature, TypeError):
        return False


async def validate_url(url: str) -> dict:
    """Validate and normalize URL, then verify if it responds"""
    try:
        url = url.strip()
        if not url:
            return {"valid": False, "error": "INVALID_URL"}
        
        # Add scheme if missing
        if not re.match(r'^https?://', url, re.IGNORECASE):
            url = 'http://' + url
        
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {"valid": False, "error": "INVALID_URL"}
        
        # Normalize URL
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
        # Verify URL responds
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            try:
                response = await client.head(normalized)
                if response.status_code >= 400:
                    return {"valid": False, "error": "INVALID_URL"}
            except httpx.HTTPError:
                return {"valid": False, "error": "INVALID_URL"}
        
        return {"valid": True, "url": normalized}
        
    except Exception:
        return {"valid": False, "error": "INVALID_URL"}


def generate_rss_xml(base_url: str) -> str:
    """Generate RSS XML from database feed table"""
    # Create RSS root element
    rss = Element('rss', version='2.0')
    channel = SubElement(rss, 'channel')
    
    # Channel metadata
    SubElement(channel, 'title').text = 'Tsuru (鶴)'
    SubElement(channel, 'link').text = base_url
    SubElement(channel, 'description').text = 'Custom RSS feed from collected articles'
    SubElement(channel, 'language').text = 'en-us'
    SubElement(channel, 'lastBuildDate').text = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    # Fetch feed items from database
    feeds = get_feed_entries(limit=100)
    
    # Add items to RSS
    for feed in feeds:
        item = SubElement(channel, 'item')
        SubElement(item, 'title').text = feed['title'] or 'No Title'
        SubElement(item, 'link').text = feed['url']
        SubElement(item, 'description').text = feed['content'] or ''
        
        # Generate guid from URL hash
        guid = hashlib.sha256(feed['url'].encode()).hexdigest()[:12]
        SubElement(item, 'guid').text = guid
        
        if feed['published_date']:
            SubElement(item, 'pubDate').text = feed['published_date']
        else:
            SubElement(item, 'pubDate').text = feed['created_at']
        
        # Add audio enclosure if TTS audio is available
        if feed['audio_path'] and feed['tts_enabled']:
            audio_path = feed['audio_path']
            if os.path.exists(audio_path):
                # Get file size
                file_size = os.path.getsize(audio_path)
                
                # Construct audio URL
                audio_filename = os.path.basename(audio_path)
                audio_url = f"{base_url}/audio/{audio_filename}"
                
                # Add enclosure element
                enclosure = SubElement(item, 'enclosure')
                enclosure.set('url', audio_url)
                enclosure.set('length', str(file_size))
                enclosure.set('type', 'audio/wav')
    
    # Pretty print XML with proper UTF-8 encoding
    xml_str = tostring(rss, encoding='utf-8', method='xml')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ', encoding='utf-8')
    return pretty_xml.decode('utf-8')
