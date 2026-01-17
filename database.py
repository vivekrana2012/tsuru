"""Database operations for RSS Feed Manager"""
import sqlite3
import hashlib
import os
from datetime import datetime
from typing import Optional

# Database path - use data directory if available
DATA_DIR = os.getenv('DATA_DIR', '.')
DB_PATH = os.path.join(DATA_DIR, 'rss_feed.db')


def init_db():
    """Initialize database from SQL file"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        with open('init.sql', 'r') as f:
            cursor.executescript(f.read())
        conn.commit()


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        return dict(user) if user else None


def update_user_password(username: str, hashed_password: str):
    """Update user password"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (hashed_password, username)
        )
        conn.commit()


def store_feed(url: str, title: str, description: str, username: str, tts_enabled: bool = False) -> bool:
    """Store feed entry in database"""
    try:
        # Use current UTC time for published date
        published = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        
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


def get_pending_tts_queue_items(limit: int = 1):
    """Get pending TTS queue items"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM tts_queue WHERE status = 'pending' ORDER BY created_at ASC LIMIT ?",
            (limit,)
        )
        return cursor.fetchall()


def update_tts_queue_status(item_id: int, status: str, error_message: Optional[str] = None):
    """Update TTS queue item status"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if error_message:
            cursor.execute(
                "UPDATE tts_queue SET status = ?, error_message = ?, processed_at = ? WHERE id = ?",
                (status, error_message, datetime.utcnow(), item_id)
            )
        else:
            cursor.execute(
                "UPDATE tts_queue SET status = ?, processed_at = ? WHERE id = ?",
                (status, datetime.utcnow(), item_id)
            )
        conn.commit()


def store_feed_with_audio(url: str, title: str, description: str, username: str, audio_path: str) -> bool:
    """Store feed entry with TTS audio path"""
    try:
        published = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO feed (url, title, content, published_date, added_by, tts_enabled, audio_path) 
                   VALUES (?, ?, ?, ?, ?, 1, ?)""",
                (url, title, description, published, username, audio_path)
            )
            conn.commit()
        
        return True
    except Exception:
        return False


def get_feed_entries(limit: int = 100):
    """Get feed entries for RSS generation"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM feed ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return cursor.fetchall()
