"""Home page route handler"""
from fastapi import Request, Cookie
from fastapi.responses import RedirectResponse
from typing import Optional

from auth import verify_session, get_session_user
from routes.utils import templates, generate_csrf_token, VERSION


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
