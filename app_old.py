from fastapi import FastAPI, Request, Form, Cookie, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from urllib.parse import urlparse, urlunparse
from passlib.context import CryptContext
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from itsdangerous import URLSafeTimedSerializer, BadSignature
import httpx
import re
import sqlite3
import secrets
import hashlib
import os
import asyncio
from datetime import datetime
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

# Load version
with open('VERSION', 'r') as f:
    VERSION = f.read().strip()

app = FastAPI()

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CSRF token generator
SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))
csrf_serializer = URLSafeTimedSerializer(SECRET_KEY)

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Password hashing context
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Session storage (in production, use Redis or similar)
sessions = {}

# Database path - use data directory if available
DATA_DIR = os.getenv('DATA_DIR', '.')
DB_PATH = os.path.join(DATA_DIR, 'rss_feed.db')

# CSRF protection functions
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

# Database initialization
def init_db():
    """Initialize database from SQL file"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        with open('init.sql', 'r') as f:
            cursor.executescript(f.read())
        conn.commit()

# Initialize database on startup
init_db()

# Create audio directory
AUDIO_DIR = os.path.join(DATA_DIR, 'audio')
os.makedirs(AUDIO_DIR, exist_ok=True)

def verify_session(session_id: Optional[str]) -> bool:
    """Verify if session is valid"""
    if not session_id:
        return False
    return session_id in sessions


def add_to_tts_queue(url: str, title: str, description: str, username: str) -> bool:
    """Add entry to TTS processing queue"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tts_queue (url, title, description, added_by, status) VALUES (?, ?, ?, ?, 'pending')",
                (url, title, description, username)
            )
            conn.commit()
        return True
    except Exception:
        return False


def store_feed(url: str, title: str, description: str, username: str, tts_enabled: bool = False) -> bool:
    """Store feed entry in database"""
    try:
        # Generate guid from URL hash
        guid = hashlib.sha256(url.encode()).hexdigest()[:12]
        
        # Use current UTC time for published date
        published = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Store in database
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO feed (url, title, content, published_date, added_by, tts_enabled) VALUES (?, ?, ?, ?, ?, ?)",
                (url, title, description, published, username, 1 if tts_enabled else 0)
            )
            conn.commit()
        
        return True
    except Exception:
        return False


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
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM feed ORDER BY created_at DESC LIMIT 100"
        )
        feeds = cursor.fetchall()
    
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


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse("login.html", {
        "request": request,
        "csrf_token": csrf_token
    })


@app.post("/login", response_class=HTMLResponse)
@limiter.limit("5/minute")
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
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
    
    if not user:
        new_token = generate_csrf_token()
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password", "csrf_token": new_token}
        )
    
    # Check if password is NULL - redirect to setup
    if user['password'] is None:
        # Store username in session for setup
        session_id = secrets.token_urlsafe(32)
        sessions[session_id] = {'username': username, 'setup_mode': True}
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
    if pwd_context.verify(password, user['password']):
        # Create session
        session_id = secrets.token_urlsafe(32)
        sessions[session_id] = {'username': username}
        
        # Redirect to home with session cookie
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


@app.get("/logout")
async def logout(session_id: Optional[str] = Cookie(None)):
    """Handle logout"""
    if session_id:
        sessions.pop(session_id, None)
    
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session_id")
    return response


@app.get("/setup-password", response_class=HTMLResponse)
async def setup_password_page(request: Request, session_id: Optional[str] = Cookie(None)):
    """Display password setup page"""
    if not session_id or session_id not in sessions or not sessions[session_id].get('setup_mode'):
        return RedirectResponse(url="/login", status_code=303)
    
    username = sessions[session_id]['username']
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse("setup_password.html", {
        "request": request, 
        "username": username,
        "csrf_token": csrf_token
    })


@app.post("/setup-password", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def setup_password(request: Request, password: str = Form(...), 
                        confirm_password: str = Form(...), csrf_token: str = Form(...),
                        session_id: Optional[str] = Cookie(None)):
    """Handle password setup"""
    if not session_id or session_id not in sessions or not sessions[session_id].get('setup_mode'):
        return RedirectResponse(url="/login", status_code=303)
    
    username = sessions[session_id]['username']
    
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
    hashed_password = pwd_context.hash(password)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (hashed_password, username)
        )
        conn.commit()
    
    # Update session to normal mode
    sessions[session_id] = {'username': username}
    
    # Redirect to home
    return RedirectResponse(url="/", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session_id: Optional[str] = Cookie(None)):
    """Display home page (requires authentication)"""
    if not verify_session(session_id):
        return RedirectResponse(url="/login", status_code=303)
    
    username = sessions[session_id]['username']
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "username": username,
        "csrf_token": csrf_token,
        "version": VERSION
    })


@app.post("/submit", response_class=HTMLResponse)
@limiter.limit("10/minute")
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
    
    username = sessions[session_id]['username']
    
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


@app.get("/feed.xml")
async def rss_feed(request: Request):
    """Serve RSS XML feed"""
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    xml_content = generate_rss_xml(base_url)
    return Response(content=xml_content, media_type="application/rss+xml; charset=utf-8")


# TTS Queue Processing Functions
async def process_tts_queue():
    """Process pending TTS queue entries"""
    try:
        import trafilatura
        import google.generativeai as genai
        
        # Configure Gemini API
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("Warning: GEMINI_API_KEY not set. TTS processing disabled.")
            return
        
        genai.configure(api_key=api_key)
        
        # Get pending queue items (limit to 1 due to Gemini rate limits)
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tts_queue WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
            )
            queue_items = cursor.fetchall()
        
        for item in queue_items:
            try:
                # Update status to processing
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE tts_queue SET status = 'processing' WHERE id = ?",
                        (item['id'],)
                    )
                    conn.commit()
                
                # Download and extract content using trafilatura
                downloaded = trafilatura.fetch_url(item['url'])
                if not downloaded:
                    raise Exception("Failed to download URL content")
                
                content = trafilatura.extract(downloaded)
                if not content:
                    raise Exception("Failed to extract text content from page")
                
                # Truncate content if too long (Gemini has token limits)
                max_chars = 30000
                if len(content) > max_chars:
                    content = content[:max_chars] + "..."
                
                # Step 1: Format content for TTS using Gemma model
                formatting_model = genai.GenerativeModel('gemma-2-27b-it')
                
                formatting_prompt = f"""You are a transcript formatter for text-to-speech systems. Your task is to take the following article content and format it as a clean, natural-sounding transcript suitable for TTS.

Remove any: URLs, email addresses, navigation elements, advertisements, meta information, HTML artifacts, and redundant formatting.

Make it flow naturally for audio narration. Return ONLY the formatted transcript text with no explanations, no markdown, no headings, no preamble - just the clean transcript.

Title: {item['title']}

Content:
{content}

Remember: Return ONLY the transcript text, nothing else."""

                formatting_response = formatting_model.generate_content(formatting_prompt)
                formatted_transcript = formatting_response.text.strip()
                
                if not formatted_transcript:
                    raise Exception("Failed to generate formatted transcript")
                
                # Step 2: Generate audio using Gemini TTS
                tts_model = genai.GenerativeModel('gemini-2.0-flash-exp')
                
                tts_response = tts_model.generate_content(
                    formatted_transcript,
                    generation_config={
                        'response_modalities': ['AUDIO']
                    }
                )
                
                # Save audio file
                audio_filename = f"{hashlib.sha256(item['url'].encode()).hexdigest()[:12]}.wav"
                audio_path = os.path.join(AUDIO_DIR, audio_filename)
                
                # Write audio data
                if hasattr(tts_response, 'audio') and tts_response.audio:
                    with open(audio_path, 'wb') as f:
                        f.write(tts_response.audio)
                else:
                    raise Exception("No audio data received from Gemini API")
                
                # Store in feed table with audio path
                published = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """INSERT INTO feed (url, title, content, published_date, added_by, tts_enabled, audio_path) 
                           VALUES (?, ?, ?, ?, ?, 1, ?)""",
                        (item['url'], item['title'], item['description'], published, item['added_by'], audio_path)
                    )
                    conn.commit()
                
                # Update queue status to completed
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE tts_queue SET status = 'completed', processed_at = ? WHERE id = ?",
                        (datetime.utcnow(), item['id'])
                    )
                    conn.commit()
                
                print(f"Successfully processed TTS for: {item['title']}")
                
            except Exception as e:
                error_msg = str(e)
                print(f"Error processing TTS queue item {item['id']}: {error_msg}")
                
                # Update queue status to failed
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE tts_queue SET status = 'failed', error_message = ?, processed_at = ? WHERE id = ?",
                        (error_msg, datetime.utcnow(), item['id'])
                    )
                    conn.commit()
    
    except Exception as e:
        print(f"Error in TTS queue processing: {str(e)}")


async def tts_worker():
    """Background worker that processes TTS queue every minute"""
    while True:
        try:
            await process_tts_queue()
        except Exception as e:
            print(f"TTS worker error: {str(e)}")
        
        # Wait 60 seconds before next poll
        await asyncio.sleep(60)


@app.on_event("startup")
async def start_tts_worker():
    """Start the TTS worker on application startup"""
    asyncio.create_task(tts_worker())


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
