# CORS Configuration Fix for CoachIntel

## Problem Solved
```
Access to fetch at 'https://api.coachintel.ai/session' from origin 'https://www.coachintel.ai' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## Root Cause
- Backend CORS was only configured for `https://coachintel.ai` (root domain)
- Frontend was making requests from `https://www.coachintel.ai` (www subdomain)
- Missing `/session` endpoint that frontend expected

## Fixes Applied

### 1. Enhanced CORS Configuration
**File**: `backend/app/main.py`

**Before**:
```python
allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", FRONTEND_URL]
```

**After**:
```python
# Automatically creates both www and non-www variants
frontend_origins = [FRONTEND_URL]
if FRONTEND_URL.startswith("https://"):
    if "www." in FRONTEND_URL:
        frontend_origins.append(FRONTEND_URL.replace("://www.", "://"))
    else:
        frontend_origins.append(FRONTEND_URL.replace("://", "://www."))

allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"] + frontend_origins
```

### 2. Added Missing `/session` Endpoint
```python
@app.get("/session")
async def get_session(user: User = Depends(verify_jwt_user)):
    """Get current user session information"""
    return {
        "user": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "name": f"{user.first_name} {user.last_name}".strip()
        },
        "authenticated": True
    }
```

### 3. Added CORS Debug Logging
```python
logger.info(f"CORS configured for origins: {['http://localhost:3000', 'http://127.0.0.1:3000'] + frontend_origins}")
```

## Railway Environment Variable Required

Make sure `FRONTEND_URL` is set in Railway to:
```
FRONTEND_URL=https://coachintel.ai
```

The code will automatically allow both:
- `https://coachintel.ai` (root domain)
- `https://www.coachintel.ai` (www subdomain)

## Testing CORS

After deployment, you can test CORS with:
```bash
# Test from www subdomain
curl -H "Origin: https://www.coachintel.ai" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://api.coachintel.ai/session

# Test from root domain  
curl -H "Origin: https://coachintel.ai" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://api.coachintel.ai/session
```

Both should return CORS headers allowing the requests.

## Expected Railway Logs

After deployment, you should see:
```
CORS configured for origins: ['http://localhost:3000', 'http://127.0.0.1:3000', 'https://coachintel.ai', 'https://www.coachintel.ai']
```

## Status: ✅ Fixed

- CORS now allows both www and non-www variants
- Added missing `/session` endpoint
- Added debug logging for troubleshooting
