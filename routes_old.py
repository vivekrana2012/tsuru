"""Route handlers for RSS Feed Manager"""
from fastapi import Request, Form, Cookie, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from urllib.parse import urlparse, urlunparse
from slowapi import Limiter
from slowapi.util import get_remote_address
from itsdangerous import URLSafeTimedSerializer, BadSignature
import httpx
import re
import secrets
import hashlib
import os
from datetime import datetime
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from database import (
    get_user_by_username,
    update_user_password,
    store_feed,
    add_to_tts_queue,
    get_feed_entries
)
from auth import (
    verify_session,
    create_session,
    get_session_user,
    is_setup_mode,
    end_setup_mode,
    delete_session,
    hash_password,
    verify_password
)

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
    
    # Pretty print XML with proper UTF-8 encoding
    xml_str = tostring(rss, encoding='utf-8', method='xml')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ', encoding='utf-8')
    return pretty_xml.decode('utf-8')


# Route: Login page (GET)
async def login_page(request: Request):
    """Display login page"""
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse("login.html", {
        "request": request,
        "csrf_token": csrf_token
    })


# Route: Login submission (POST)
async def login(request: Request, username: str = Form(...), password: str = Form(...),
               csrf_token: str = Form(...)):
    """Handle login submission"""
    # Validate CSRF token
    if not validate_csrf_token(csrf_token):
        new_token = generate_csrf_token()
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid security token", "csrf_token": new_token}
        )
    
    user = get_user_by_username(username)
    
    if not user:
        new_token = generate_csrf_token()
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password", "csrf_token": new_token}
        )
    
    # Check if password is NULL - redirect to setup
    if user['password'] is None:
        session_id = create_session(username, setup_mode=True)
        response = RedirectResponse(url="/setup-password", status_code=303)
        response.set_cookie(
            key="session_id", 
            value=session_id, 
            httponly=True, 
            secure=True, 
            samesite='lax'
        )
        return response
    
    # Verify credentials
    if verify_password(password, user['password']):
        session_id = create_session(username)
        
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="session_id", 
            value=session_id, 
            httponly=True, 
            secure=True, 
            samesite='lax'
        )
        return response
    
    new_token = generate_csrf_token()
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password", "csrf_token": new_token}
    )


# Route: Logout
async def logout(session_id: Optional[str] = Cookie(None)):
    """Handle logout"""
    if session_id:
        delete_session(session_id)
    
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session_id")
    return response


# Route: Setup password page (GET)
async def setup_password_page(request: Request, session_id: Optional[str] = Cookie(None)):
    """Display password setup page"""
    if not session_id or not is_setup_mode(session_id):
        return RedirectResponse(url="/login", status_code=303)
    
    username = get_session_user(session_id)
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse("setup_password.html", {
        "request": request, 
        "username": username,
        "csrf_token": csrf_token
    })


# Route: Setup password submission (POST)
async def setup_password(request: Request, password: str = Form(...), 
                        confirm_password: str = Form(...), csrf_token: str = Form(...),
                        session_id: Optional[str] = Cookie(None)):
    """Handle password setup"""
    if not session_id or not is_setup_mode(session_id):
        return RedirectResponse(url="/login", status_code=303)
    
    username = get_session_user(session_id)
    
    # Validate CSRF token
    if not validate_csrf_token(csrf_token):
        new_token = generate_csrf_token()
        return templates.TemplateResponse(
            "setup_password.html",
            {"request": request, "username": username, "error": "Invalid security token", "csrf_token": new_token}
        )
    
    # Validate passwords match
    if password != confirm_password:
        new_token = generate_csrf_token()
        return templates.TemplateResponse(
            "setup_password.html",
            {"request": request, "username": username, "error": "Passwords do not match", "csrf_token": new_token}
        )
    
    # Validate password length
    if len(password) < 6:
        new_token = generate_csrf_token()
        return templates.TemplateResponse(
            "setup_password.html",
            {"request": request, "username": username, "error": "Password must be at least 6 characters", "csrf_token": new_token}
        )
    
    # Hash and save password
    hashed_password = hash_password(password)
    update_user_password(username, hashed_password)
    
    # End setup mode
    end_setup_mode(session_id)
    
    # Redirect to home
    return RedirectResponse(url="/", status_code=303)


# Route: Home page (GET)
async def home(request: Request, session_id: Optional[str] = Cookie(None)):
    """Display home page (requires authentication)"""
    if not verify_session(session_id):
        return RedirectResponse(url="/login", status_code=303)
    
    username = get_session_user(session_id)
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "username": username,
        "csrf_token": csrf_token,
        "version": VERSION
    })


# Route: Submit URL (POST)
async def submit(request: Request, 
                url: str = Form(..., max_length=2000),
                title: str = Form(..., max_length=200), 
                description: str = Form(..., max_length=1000),
                tts: Optional[str] = Form(None),
                csrf_token: str = Form(...),
                session_id: Optional[str] = Cookie(None)):
    """Handle URL submission (requires authentication)"""
    if not verify_session(session_id):
        return RedirectResponse(url="/login", status_code=303)
    
    username = get_session_user(session_id)
    
    # Check if TTS is enabled
    tts_enabled = tts == "true"
    
    # Validate CSRF token
    if not validate_csrf_token(csrf_token):
        new_token = generate_csrf_token()
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": "Invalid security token", "username": username, "csrf_token": new_token, "version": VERSION}
        )
    
    # Validate and normalize URL
    validation_result = await validate_url(url)
    
    if not validation_result["valid"]:
        new_token = generate_csrf_token()
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": validation_result["error"], "username": username, "csrf_token": new_token, "version": VERSION}
        )
    
    normalized_url = validation_result["url"]
    
    # If TTS is enabled, add to queue instead of directly storing
    if tts_enabled:
        queued = add_to_tts_queue(normalized_url, title, description, username)
        new_token = generate_csrf_token()
        if queued:
            return templates.TemplateResponse(
                "index.html", 
                {"request": request, "submitted_url": normalized_url, "message": "Added to TTS queue for processing", "username": username, "csrf_token": new_token, "version": VERSION}
            )
        else:
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "error": "Failed to add to TTS queue", "username": username, "csrf_token": new_token, "version": VERSION}
            )
    
    # Store feed entry directly (non-TTS)
    stored = store_feed(normalized_url, title, description, username, tts_enabled=False)
    
    new_token = generate_csrf_token()
    if stored:
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "submitted_url": normalized_url, "username": username, "csrf_token": new_token, "version": VERSION}
        )
    else:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": "Failed to store feed entry", "username": username, "csrf_token": new_token, "version": VERSION}
        )


# Route: RSS Feed (GET)
async def rss_feed(request: Request):
    """Serve RSS XML feed"""
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    xml_content = generate_rss_xml(base_url)
    return Response(content=xml_content, media_type="application/rss+xml; charset=utf-8")
