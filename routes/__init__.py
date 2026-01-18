"""Routes package - imports all route handlers"""
from routes.login import login_page, login, logout
from routes.setup import setup_password_page, setup_password
from routes.home import home
from routes.submit import submit
from routes.feed import rss_feed
from routes.utils import limiter

__all__ = [
    'login_page',
    'login',
    'logout',
    'setup_password_page',
    'setup_password',
    'home',
    'submit',
    'rss_feed',
    'limiter'
]
