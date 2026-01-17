"""URL submission route handler"""
from fastapi import Request, Form, Cookie
from typing import Optional

from database import store_feed, add_to_tts_queue
from auth import verify_session, get_session_user
from routes.utils import templates, generate_csrf_token, validate_csrf_token, validate_url, VERSION
from fastapi.responses import RedirectResponse


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
