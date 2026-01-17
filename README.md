# RSS Feed Manager - Tsuru (鶴)

**Version: 2.0.0**

A minimalist RSS feed manager built with FastAPI and a markdown-inspired UI design. Add custom feed entries with URLs, titles, and descriptions, then generate and serve your own RSS feed.

## Features

- **User Authentication**: Secure login with password hashing using passlib
- **First-time Setup**: Admin user with password setup on first login (safe for git)
- **Feed Management**: Add custom feed entries with URL validation
- **Text-to-Speech (TTS)**: Optional TTS processing using Google Gemini API
  - Automatic content extraction from URLs using trafilatura
  - Two-step pipeline: content formatting + audio generation
  - Background queue processing (1 request/minute to comply with API limits)
  - Audio files stored in WAV format
- **RSS Feed Generation**: Automatically generates RSS 2.0 XML feed with podcast support
- **Podcast-Ready**: RSS enclosure tags for TTS audio files (compatible with podcast apps)
- **Markdown-style UI**: Clean, minimalist interface with monospace fonts
- **SQLite Database**: Lightweight data storage
- **Modular Architecture**: Clean separation of concerns (database, auth, routes, services)
- **Security Features**:
  - CSRF protection on all forms
  - Rate limiting on authentication endpoints
  - Input length validation
  - Secure cookie flags (httponly, secure, samesite)

## Requirements

- Python 3.8+
- pip
- Docker (optional, for containerized deployment)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd project_rss_feed
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running Locally

1. Start the application:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

### Running with Docker

**IMPORTANT**: Set a SECRET_KEY for production use!

1. Create a `.env` file:
```bash
cp .env.example .env
# Generate a secure key
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Edit .env and add your SECRET_KEY
```

2. Start with Docker Compose:
```bash
docker-compose up -d
```

Or manually:

1. Build the Docker image:
```bash
docker build -t rss-feed-manager .
```

2. Run the container:
```bash
docker run -d -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e SECRET_KEY=your-secret-key-here \
  -e GEMINI_API_KEY=your-gemini-api-key-here \
  --name rss-feed rss-feed-manager
```

The database will be stored in the `./data` directory on your host system.

### First-time Setup

1. **Access the application**:
   - Open browser to `http://localhost:8000`
   - You'll be redirected to the login page

2. **Initial login**:
   - Username: `admin`
   - Password: (leave empty on first visit)

3. **Set your password**:
   - You'll be prompted to set a secure password
   - Enter and confirm your new password (minimum 6 characters)

4. **Add feed entries**:
   - Enter URL, title, and description
   - Optionally check "TTS" checkbox to enable text-to-speech for this entry
   - Click "Add" to save the entry
   - URL is validated both client-side and server-side
   - TTS entries are queued for background processing

5. **Access your RSS feed**:
```
http://localhost:8000/feed.xml
```

## Project Structure

```
project_rss_feed/
├── app.py                      # Main FastAPI application entry point
├── database.py                 # Database operations
├── auth.py                     # Authentication and session management
├── gemini_service.py           # Google Gemini API integration for TTS
├── tts_worker.py               # Background TTS queue processor
├── routes/                     # Modular route handlers
│   ├── __init__.py            # Package exports
│   ├── utils.py               # Shared utilities (CSRF, RSS generation, URL validation)
│   ├── login.py               # Login/logout routes
│   ├── setup.py               # Password setup routes
│   ├── home.py                # Home page route
│   ├── submit.py              # URL submission route
│   └── feed.py                # RSS feed route
├── templates/                  # Jinja2 templates
│   ├── index.html             # Main feed management page
│   ├── login.html             # Login page
│   └── setup_password.html    # Password setup page
├── init.sql                    # Database schema and initial data
├── requirements.txt            # Python dependencies
├── VERSION                     # Version number file
├── CHANGELOG.md                # Version history and changes
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Docker Compose configuration
├── .env.example                # Environment variables template
├── .gitignore                 # Git ignore rules
├── LICENSE                    # MIT License
└── README.md                  # This file
```

## Database Schema

### users table
- `id`: Primary key
- `username`: Unique username
- `password`: Hashed password (NULL for first-time setup)
- `created_at`: Account creation timestamp

### feed table
- `id`: Primary key
- `url`: Feed entry URL
- `title`: Entry title
- `content`: Entry description
- `published_date`: Publication date (RFC 822 format)
- `added_by`: Username who added the entry
- `tts_enabled`: TTS flag (0 or 1)
- `audio_path`: Path to generated audio file (for TTS entries)
- `created_at`: Entry creation timestamp

### tts_queue table
- `id`: Primary key
- `url`: URL to process
- `title`: Entry title
- `description`: Entry description
- `added_by`: Username who added the entry
- `status`: Processing status (pending/processing/completed/failed)
- `error_message`: Error details (if failed)
- `created_at`: Queue entry creation timestamp
- `processed_at`: When processing completed

## Configuration

### Environment Variables
- **SECRET_KEY**: Secret key for CSRF token generation (REQUIRED for production)
- **GEMINI_API_KEY**: Google Gemini API key for TTS functionality (get from https://aistudio.google.com/app/apikey)
- **PORT**: Port to run the application on (default: 8000)
- **DATA_DIR**: Directory where database will be stored (default: current directory)

### Default Settings
- **Default username**: admin
- **Default password**: Must be set on first login
- **Database**: rss_feed.db (SQLite)
- **Session Storage**: In-memory (use Redis for production)
- **Rate Limits**: 
  - Authentication endpoints: 5 requests/minute
  - Feed submission: 10 requests/minute
  - Gemini API (TTS): 1 request/minute
- **Input Limits**:
  - URL: 2000 characters
  - Title: 200 characters
  - Description: 1000 characters
- **TTS Queue**: Processes 1 item every 60 seconds (background worker)
- **Audio Format**: WAV files stored in `data/audio/` directory

### Docker Volume Mounting
The Docker setup uses a volume mount to persist database and audio files:
```bash
# The data directory on host is mapped to /app/data in container
-v $(pwd)/data:/app/data
```

This ensures your database and TTS audio files persist across container restarts.

### Security Notes
- **Passwords**: Hashed using pbkdf2_sha256
- **Sessions**: Secure token generation with httponly, secure, and samesite flags
- **CSRF Protection**: All forms protected with time-limited CSRF tokens (1-hour expiry)
- **Rate Limiting**: Protection against brute-force attacks
- **Input Validation**: Length limits and URL verification
- **Database**: File excluded from git via .gitignore
- **Default admin**: Requires password setup on first use (safe for git)
- **SECRET_KEY**: Must be set for production to maintain sessions across restarts

## RSS Feed Format

The generated RSS feed follows RSS 2.0 specification with:
- Channel metadata (title, link, description)
- Item entries with:
  - Title
  - Link (URL)
  - Description (content)
  - GUID (SHA256 hash of URL, first 12 characters)
  - Publication date (RFC 822 format)
  - Enclosure (for TTS audio files):
    - URL to audio file
    - File size in bytes
    - MIME type (audio/wav)

### Podcast Support
The RSS feed includes podcast-compatible enclosure tags for entries with TTS-generated audio. This makes the feed compatible with podcast apps like Apple Podcasts, Spotify, and others.

## Development

### URL Validation
- Client-side: JavaScript validation before submission
- Server-side: URL parsing, normalization, and HTTP verification

### Feed Entry Processing
- URLs are normalized (scheme/netloc to lowercase)
- GUID generated from SHA256 hash of URL
- Publication date set to current UTC time
- All entries stored with username who added them

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software without restrictions.
