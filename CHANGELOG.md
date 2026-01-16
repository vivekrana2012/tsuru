# Changelog

All notable changes to Tsuru (鶴) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-16

### Added
- User authentication with secure password hashing (pbkdf2_sha256)
- First-time password setup for admin user
- Feed entry management (URL, title, description)
- RSS 2.0 XML feed generation at `/feed.xml`
- URL validation (client-side and server-side)
- CSRF protection on all forms
- Rate limiting (5/min on auth, 10/min on feed submission)
- Input length validation (URL: 2000, title: 200, description: 1000 chars)
- Secure cookie flags (httponly, secure, samesite)
- Markdown-inspired minimalist UI
- SQLite database storage
- Docker support with volume mounting
- Environment variable configuration (SECRET_KEY, PORT, DATA_DIR)
- Version tracking system

### Security
- CSRF tokens with 1-hour expiry
- Rate limiting protection against brute-force attacks
- Secure session management
- Input validation and sanitization
- HTTP-only and secure cookies

## Future Versions

### [2.0.0] - Planned
- (Add your planned features here)
