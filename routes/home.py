"""Home page route handler"""
from fastapi import Request, Cookie
from fastapi.responses import RedirectResponse
from typing import Optional

from auth import verify_session, get_session_user
from routes.utils import templates, generate_csrf_token, get_base_path, VERSION


async def home(request: Request, session_id: Optional[str] = Cookie(None)):
    """Display home page (requires authentication)"""
    base_path = get_base_path(request)
    if not verify_session(session_id):
        return RedirectResponse(url=f"{base_path}/login", status_code=303)
    
    username = get_session_user(session_id)
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "username": username,
        "csrf_token": csrf_token,
        "version": VERSION,
        "base_path": base_path
    })
