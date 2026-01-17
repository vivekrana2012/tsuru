"""Main application entry point for Tsuru RSS Feed Manager"""
import os
import asyncio
from fastapi import FastAPI, Request, Form, Cookie
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import Optional

from database import init_db
from routes import (
    limiter,
    login_page,
    login,
    logout,
    setup_password_page,
    setup_password,
    home,
    submit,
    rss_feed
)
from tts_worker import tts_worker

# Initialize FastAPI app
app = FastAPI()

# Setup rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create audio directory
DATA_DIR = os.getenv('DATA_DIR', '.')
AUDIO_DIR = os.path.join(DATA_DIR, 'audio')
os.makedirs(AUDIO_DIR, exist_ok=True)

# Mount audio directory for serving audio files
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

# Initialize database on startup
init_db()


# Register routes
@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return await login_page(request)


@app.post("/login", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def post_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...)
):
    return await login(request, username, password, csrf_token)


@app.get("/logout")
async def get_logout(session_id: Optional[str] = Cookie(None)):
    return await logout(session_id)


@app.get("/setup-password", response_class=HTMLResponse)
async def get_setup_password(request: Request, session_id: Optional[str] = Cookie(None)):
    return await setup_password_page(request, session_id)


@app.post("/setup-password", response_class=HTMLResponse)
@limiter.limit("5/minute")
async def post_setup_password(
    request: Request,
    password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
    session_id: Optional[str] = Cookie(None)
):
    return await setup_password(request, password, confirm_password, csrf_token, session_id)


@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request, session_id: Optional[str] = Cookie(None)):
    return await home(request, session_id)


@app.post("/submit", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def post_submit(
    request: Request,
    url: str = Form(..., max_length=2000),
    title: str = Form(..., max_length=200),
    description: str = Form(..., max_length=1000),
    tts: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    session_id: Optional[str] = Cookie(None)
):
    return await submit(request, url, title, description, tts, csrf_token, session_id)


@app.get("/feed.xml")
async def get_rss_feed(request: Request):
    return await rss_feed(request)


@app.on_event("startup")
async def start_tts_worker():
    """Start the TTS worker on application startup"""
    asyncio.create_task(tts_worker())


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
