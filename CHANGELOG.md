# Changelog

All notable changes to Tsuru (鶴) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-01-17

### Added
- TTS (Text-to-Speech) functionality with Google Gemini API integration
- TTS queue system for background processing
- Background worker that polls TTS queue every minute
- Content extraction using trafilatura
- Two-step TTS pipeline: content formatting (gemma-2-27b-it) + audio generation (gemini-2.0-flash-exp)
- Audio file storage in data/audio directory
- TTS checkbox on submission form

### Changed
- Refactored codebase into modular structure:
  - `database.py` - Database operations
  - `auth.py` - Authentication and session management
  - `gemini_service.py` - Gemini API integration
  - `tts_worker.py` - Background TTS queue processor
  - `routes/` package - Modular route handlers (login, setup, home, submit, feed)
- Database schema updated with `tts_queue` table and TTS-related columns in `feed` table
- Rate limiting: 1 Gemini API request per minute to comply with API limits

### Infrastructure
- Added GEMINI_API_KEY environment variable
- Updated requirements.txt with google-generativeai package
- Updated Dockerfile to copy new modular files
- Enhanced docker-compose.yml with GEMINI_API_KEY configuration

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
