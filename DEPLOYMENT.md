# Flexible Path Deployment Guide

This application now supports flexible deployment paths using FastAPI's `root_path` feature. You can deploy at the root of your domain or any sub-path using nginx reverse proxy.

## Quick Start

### Local Development (Root Path)
```bash
python app.py
# Access at http://localhost:8000
```

### Docker with Root Path
```bash
# No ROOT_PATH needed
docker-compose up -d
# Access at http://localhost:8000
```

### Docker with Sub-path
```bash
# Set ROOT_PATH in docker-compose.yml or .env
ROOT_PATH=/manage docker-compose up -d
# Configure nginx to forward /manage/ to container
# Access at http://your-domain.com/manage/
```

## How It Works

### Application Architecture

1. **FastAPI root_path**: Set via `ROOT_PATH` environment variable
   ```python
   app = FastAPI(root_path=os.getenv('ROOT_PATH', ''))
   ```

2. **Base path utility**: Extracts root_path from request scope
   ```python
   def get_base_path(request: Request) -> str:
       return request.scope.get("root_path", "")
   ```

3. **All URLs use base_path**: Templates, redirects, RSS feed
   - Templates: `{{ base_path }}/login`
   - Redirects: `f"{base_path}/login"`
   - RSS audio: `f"{base_url}{base_path}/audio/{filename}"`

### Nginx Configuration

The nginx configuration strips the sub-path before forwarding to the app:

```nginx
location /manage/ {
    proxy_pass http://localhost:8000/;  # Trailing slash is critical!
}
```

**What happens:**
1. Browser requests: `https://example.com/manage/login`
2. Nginx strips `/manage` and forwards: `http://localhost:8000/login`
3. App sees: `/login` (clean request)
4. App knows root_path is `/manage` (from environment)
5. App generates: `<form action="/manage/login">`
6. Browser receives: `/manage/login` in HTML

## Configuration Examples

### Example 1: Root Path Deployment

**Environment:**
```bash
ROOT_PATH=
# or omit ROOT_PATH entirely
```

**Nginx:**
```nginx
location / {
    proxy_pass http://localhost:8000;
}
```

**Access:**
- Login: `https://example.com/login`
- Feed: `https://example.com/feed.xml`

### Example 2: Sub-path at /manage

**Environment:**
```bash
ROOT_PATH=/manage
```

**Nginx:**
```nginx
location /manage/ {
    proxy_pass http://localhost:8000/;
}
```

**Access:**
- Login: `https://example.com/manage/login`
- Feed: `https://example.com/manage/feed.xml`

### Example 3: Sub-path at /rss/tsuru

**Environment:**
```bash
ROOT_PATH=/rss/tsuru
```

**Nginx:**
```nginx
location /rss/tsuru/ {
    proxy_pass http://localhost:8000/;
}
```

**Access:**
- Login: `https://example.com/rss/tsuru/login`
- Feed: `https://example.com/rss/tsuru/feed.xml`

## Files Modified

The following files were updated to support flexible paths:

### Core Application
- **app.py**: Added `root_path` parameter to FastAPI
- **routes/utils.py**: Added `get_base_path()` utility function

### Route Handlers
- **routes/login.py**: All redirects and template contexts include base_path
- **routes/home.py**: All redirects and template contexts include base_path
- **routes/setup.py**: All redirects and template contexts include base_path
- **routes/submit.py**: All redirects and template contexts include base_path
- **routes/feed.py**: Pass base_path to RSS generation

### Templates
- **templates/login.html**: Form action uses `{{ base_path }}/login`
- **templates/index.html**: Logout link and form action use base_path
- **templates/setup_password.html**: Form action uses `{{ base_path }}/setup-password`

### Configuration
- **docker-compose.yml**: Added `ROOT_PATH` environment variable
- **.env.example**: Added `ROOT_PATH` documentation
- **README.md**: Added comprehensive nginx deployment guide

## Testing Your Deployment

### 1. Test Locally First

```bash
# Test with root path
python app.py
# Visit http://localhost:8000

# Test with sub-path
ROOT_PATH=/manage python app.py
# Visit http://localhost:8000/manage (won't work without nginx)
```

### 2. Test with Docker

```bash
# Update docker-compose.yml
environment:
  - ROOT_PATH=/manage

# Start container
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 3. Test nginx Configuration

```bash
# Test config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Check if accessible
curl http://localhost/manage/feed.xml
```

### 4. Test All URLs

After deployment, verify these URLs work:

- [ ] Login page: `https://example.com/manage/login`
- [ ] Home page: `https://example.com/manage/`
- [ ] RSS feed: `https://example.com/manage/feed.xml`
- [ ] Audio files: `https://example.com/manage/audio/*.wav`
- [ ] Form submissions: POST to `/manage/submit`
- [ ] Redirects: Logout redirects to `/manage/login`

## Troubleshooting

### Issue: 404 on all sub-path URLs

**Symptoms:**
- `https://example.com/manage/login` returns 404
- Direct access to container works: `http://localhost:8000/login`

**Solution:**
1. Check nginx `proxy_pass` has trailing slash: `http://localhost:8000/;`
2. Verify `ROOT_PATH=/manage` is set in container
3. Restart container: `docker-compose restart`

### Issue: Redirects go to wrong path

**Symptoms:**
- Clicking logout redirects to `https://example.com/login` instead of `https://example.com/manage/login`

**Solution:**
1. Verify `ROOT_PATH` environment variable is set correctly
2. Check container logs: `docker-compose logs`
3. Ensure nginx is stripping path correctly

### Issue: CSS/Audio files not loading

**Symptoms:**
- Login page shows but looks broken
- Audio files return 404

**Solution:**
1. Check browser console for 404 errors
2. Verify nginx forwards ALL paths under `/manage/`
3. Check `ROOT_PATH` matches nginx location

### Issue: CSRF token errors

**Symptoms:**
- "Invalid security token" error on form submission

**Solution:**
1. Ensure `SECRET_KEY` is set and consistent across restarts
2. Check cookies are being set correctly (httponly, secure flags)
3. Verify nginx forwards all proxy headers:
   ```nginx
   proxy_set_header Host $host;
   proxy_set_header X-Forwarded-Proto $scheme;
   ```

## Migration from Hardcoded Paths

If you're upgrading from a version with hardcoded paths (2.0.0 or earlier):

1. **No database changes needed** - Schema unchanged
2. **Update your deployment**:
   - Set `ROOT_PATH` environment variable
   - Update nginx configuration
   - Restart container
3. **Test all URLs** - Use checklist above

## Security Notes

- All URLs maintain the same security features (CSRF, rate limiting, etc.)
- Cookies work correctly with sub-paths
- No additional security concerns with nginx reverse proxy
- Standard security headers should be set in nginx (HSTS, etc.)

## Benefits

✅ **Flexible deployment**: Run at root or any sub-path
✅ **No code changes**: Just environment configuration
✅ **Multiple instances**: Run different instances at different paths
✅ **Easy migration**: Works with or without nginx
✅ **Backwards compatible**: Empty `ROOT_PATH` = original behavior
