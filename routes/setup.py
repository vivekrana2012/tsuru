"""Password setup route handlers"""
from fastapi import Request, Form, Cookie
from fastapi.responses import RedirectResponse
from typing import Optional

from database import update_user_password
from auth import is_setup_mode, get_session_user, end_setup_mode, hash_password
from routes.utils import templates, generate_csrf_token, validate_csrf_token, get_base_path


async def setup_password_page(request: Request, session_id: Optional[str] = Cookie(None)):
    """Display password setup page"""
    base_path = get_base_path(request)
    if not session_id or not is_setup_mode(session_id):
        return RedirectResponse(url=f"{base_path}/login", status_code=303)
    
    username = get_session_user(session_id)
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse("setup_password.html", {
        "request": request, 
        "username": username,
        "csrf_token": csrf_token,
        "base_path": base_path
    })


async def setup_password(request: Request, password: str = Form(...), 
                        confirm_password: str = Form(...), csrf_token: str = Form(...),
                        session_id: Optional[str] = Cookie(None)):
    """Handle password setup"""
    base_path = get_base_path(request)
    if not session_id or not is_setup_mode(session_id):
        return RedirectResponse(url=f"{base_path}/login", status_code=303)
    
    username = get_session_user(session_id)
    
    # Validate CSRF token
    if not validate_csrf_token(csrf_token):
        new_token = generate_csrf_token()
        return templates.TemplateResponse(
            "setup_password.html",
            {"request": request, "username": username, "error": "Invalid security token", "csrf_token": new_token, "base_path": base_path}
        )
    
    # Validate passwords match
    if password != confirm_password:
        new_token = generate_csrf_token()
        return templates.TemplateResponse(
            "setup_password.html",
            {"request": request, "username": username, "error": "Passwords do not match", "csrf_token": new_token, "base_path": base_path}
        )
    
    # Validate password length
    if len(password) < 6:
        new_token = generate_csrf_token()
        return templates.TemplateResponse(
            "setup_password.html",
            {"request": request, "username": username, "error": "Password must be at least 6 characters", "csrf_token": new_token, "base_path": base_path}
        )
    
    # Hash and save password
    hashed_password = hash_password(password)
    update_user_password(username, hashed_password)
    
    # End setup mode
    end_setup_mode(session_id)
    
    # Redirect to home
    return RedirectResponse(url=f"{base_path}/", status_code=303)
