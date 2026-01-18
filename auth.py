"""Authentication and session management"""
import secrets
from typing import Optional
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Session storage (in production, use Redis or similar)
sessions = {}


def verify_session(session_id: Optional[str]) -> bool:
    """Verify if session is valid"""
    if not session_id:
        return False
    return session_id in sessions


def create_session(username: str, setup_mode: bool = False) -> str:
    """Create a new session and return session ID"""
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {'username': username}
    if setup_mode:
        sessions[session_id]['setup_mode'] = True
    return session_id


def get_session_user(session_id: str) -> Optional[str]:
    """Get username from session"""
    if session_id in sessions:
        return sessions[session_id].get('username')
    return None


def is_setup_mode(session_id: str) -> bool:
    """Check if session is in setup mode"""
    if session_id in sessions:
        return sessions[session_id].get('setup_mode', False)
    return False


def end_setup_mode(session_id: str):
    """End setup mode for session"""
    if session_id in sessions:
        sessions[session_id]['setup_mode'] = False


def delete_session(session_id: str):
    """Delete a session"""
    sessions.pop(session_id, None)


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)
