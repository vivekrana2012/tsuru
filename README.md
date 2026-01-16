# RSS Feed Manager - Tsuru (鶴)

**Version: 1.0.0**

A minimalist RSS feed manager built with FastAPI and a markdown-inspired UI design. Add custom feed entries with URLs, titles, and descriptions, then generate and serve your own RSS feed.

## Features

- **User Authentication**: Secure login with password hashing using passlib
- **First-time Setup**: Admin user with password setup on first login (safe for git)
- **Feed Management**: Add custom feed entries with URL validation
- **RSS Feed Generation**: Automatically generates RSS 2.0 XML feed
- **Markdown-style UI**: Clean, minimalist interface with monospace fonts
- **SQLite Database**: Lightweight data storage
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
  --name rss-feed rss-feed-manager
```

The database will be stored in the `./data` directory on your host system.

### First-time Setup
   -Dockerfile                  # Docker image definition
├── docker-compose.yml          # Docker Compose configuration
├── templates/
│   ├── index.html             # Main feed management page
│   ├── login.html             # Login page
│   └── setup_password.html    # Password setup page
├── data/                      # Database storage (mounted volume)
4. **Add feed entries**:
   - Enter URL, title, and description
   - Click "Add" to save the entry
   - URL is validated both client-side and server-side

5. **Access your RSS feed**:
```
http://localhost:8000/feed.xml
```

## Project Structure

```
project_rss_feed/
├── app.py                      # Main FastAPI application
├── init.sql                    # Database schema and initial data
├── requirements.txt            # Python dependencies
├── templates/
│   ├── index.html             # Main feed management page
│   ├── login.html             # Login page
│   └── setup_password.html    # Password setup page
├── .gitignore                 # Git ignore rules
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
- `created_at`: Entry creation timestamp

## Configuration

### Environment Variables
- **SECRET_KEY**: Secret key for CSRF token generation (REQUIRED for production)
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
- **Input Limits**:
  - URL: 2000 characters
  - Title: 200 characters
  - Description: 1000 characters

### Docker Volume Mounting
The Docker setup uses a volume mount to persist database files:
```bash
# The data directory on host is mapped to /app/data in container
-v $(pwd)/data:/app/data
```

This ensures your database persists across container restarts.
- **Port**: 8000
- **Database**: rss_feed.db (SQLite)
- **Session Storage**: In-memory (use Redis for production)

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
