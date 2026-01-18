"""Login and logout route handlers"""
from fastapi import Request, Form, Cookie
from fastapi.responses import RedirectResponse
from typing import Optional

from database import get_user_by_username
from auth import create_session, delete_session, verify_password
from routes.utils import templates, generate_csrf_token, validate_csrf_token, get_base_path


async def login_page(request: Request):
    """Display login page"""
    csrf_token = generate_csrf_token()
    base_path = get_base_path(request)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "csrf_token": csrf_token,
        "base_path": base_path
    })


async def login(request: Request, username: str = Form(...), password: str = Form(...),
               csrf_token: str = Form(...)):
    """Handle login submission"""
    # Validate CSRF token
    if not validate_csrf_token(csrf_token):
        new_token = generate_csrf_token()
        base_path = get_base_path(request)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid security token", "csrf_token": new_token, "base_path": base_path}
        )
    
    user = get_user_by_username(username)
    
    if not user:
        new_token = generate_csrf_token()
        base_path = get_base_path(request)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password", "csrf_token": new_token, "base_path": base_path}
        )
    
    # Check if password is NULL - redirect to setup
    if user['password'] is None:
        session_id = create_session(username, setup_mode=True)
        base_path = get_base_path(request)
        response = RedirectResponse(url=f"{base_path}/setup-password", status_code=303)
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
        base_path = get_base_path(request)
        
        response = RedirectResponse(url=f"{base_path}/", status_code=303)
        response.set_cookie(
            key="session_id", 
            value=session_id, 
            httponly=True, 
            secure=True, 
            samesite='lax'
        )
        return response
    
    new_token = generate_csrf_token()
    base_path = get_base_path(request)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password", "csrf_token": new_token, "base_path": base_path}
    )


async def logout(request: Request, session_id: Optional[str] = Cookie(None)):
    """Handle logout"""
    if session_id:
        delete_session(session_id)
    
    base_path = get_base_path(request)
    response = RedirectResponse(url=f"{base_path}/login", status_code=303)
    response.delete_cookie(key="session_id")
    return response
