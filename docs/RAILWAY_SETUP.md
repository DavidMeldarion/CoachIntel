# Railway Deployment Guide for CoachIntel Backend

## Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub account
3. Connect your GitHub repository

## Step 2: Deploy Backend
1. Click "New Project" in Railway dashboard
2. Select "Deploy from GitHub repo"
3. Choose your CoachIntel repository
4. Set the root directory to `/backend`
5. Railway will automatically detect it's a Python app

## Step 3: Configure Environment Variables
Add these environment variables in Railway dashboard:

### Database (use Supabase Connection Pooler URLs)
```
# IMPORTANT: Use connection pooler URLs from Supabase (port 6543, not 5432)
# Get these from: Supabase Dashboard → Settings → Database → Connection Pooling

# Regular connection for migrations and sync operations
DATABASE_URL=postgresql://postgres.your-project-ref:your-password@region.pooler.supabase.com:6543/postgres

# Async connection for FastAPI (MUST use postgresql+asyncpg://)
ASYNC_DATABASE_URL=postgresql+asyncpg://postgres.your-project-ref:your-password@region.pooler.supabase.com:6543/postgres

# Sync connection for Alembic migrations
SYNC_DATABASE_URL=postgresql://postgres.your-project-ref:your-password@region.pooler.supabase.com:6543/postgres
```

### Redis (will be updated with Upstash URL)
```
CELERY_BROKER_URL=redis://your-upstash-host:port
CELERY_RESULT_BACKEND=redis://your-upstash-host:port
REDIS_URL=redis://your-upstash-host:port
REDIS_HOST=your-upstash-host
REDIS_PORT=your-upstash-port
```

### API Configuration
```
OPENAI_API_KEY=your-openai-api-key
JWT_SECRET=your-secure-jwt-secret-for-production
```

### Google OAuth
```
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://api.coachintel.ai/auth/google/callback
```

### Frontend URL (IMPORTANT: Update this!)
```
FRONTEND_URL=https://coachintel.ai
```

### Email
```
EMAIL_PROVIDER=postmark
POSTMARK_API_KEY=your-postmark-api-key
```

## Step 4: Custom Start Command
Railway should automatically use the start command from railway.json:
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Step 5: Domain Configuration
1. Railway will provide a domain like: `your-app.railway.app`
2. Use this domain for your API_URL in frontend
3. Update Google OAuth redirect URI with this domain

## Step 6: Database Migration
After deployment, run database migrations:
1. Go to Railway dashboard
2. Open your service
3. Go to "Deploy" tab and find the deployment
4. Use the CLI or connect via SSH to run:
```bash
alembic upgrade head
```

## Troubleshooting

### Common Issues:
1. **Build Failures**: Check that `requirements.txt` is in the backend folder
2. **Port Binding Error**: "Invalid value for '--port': '$PORT' is not a valid integer"
   - **Solution**: Use the `start.py` script (already included)
   - **Alternative**: Remove `railway.json` and let Railway auto-detect using `Procfile`
3. **Database Connection Error**: "Network unreachable" or "Connection refused"
   - **Solution**: Use Supabase connection pooler URLs (port 6543)
   - **Check**: URLs should use `region.pooler.supabase.com`, not `db.project.supabase.co`
4. **AsyncPG Driver Error**: "The asyncio extension requires an async driver to be used"
   - **Solution**: Ensure `ASYNC_DATABASE_URL` starts with `postgresql+asyncpg://`
   - **Check**: `asyncpg` is in `requirements.txt` (already included)
5. **Prepared Statement Error**: "prepared statement already exists" or "pgbouncer with pool_mode"
   - **Solution**: Disabled prepared statements in `models.py` (already fixed)
   - **Cause**: PgBouncer connection pooling conflicts with prepared statements
   - **Technical**: Added `statement_cache_size: 0` to engine configuration
6. **Database Connection**: Verify DATABASE_URL format
6. **CORS Issues**: Make sure your frontend domain is allowed

### Port Binding Error Fix:
If you see the PORT error, try these solutions in order:

**Option 1: Use start.py script (Recommended)**
```bash
# This should work with the current setup
# The start.py script handles PORT properly
```

**Option 2: Manual Railway Configuration**
1. Go to Railway dashboard → Your service → Settings
2. Under "Deploy", set custom start command:
   ```
   python start.py
   ```

**Option 3: Remove railway.json**
1. Delete `railway.json` from your repository
2. Let Railway use the `Procfile` instead
3. Redeploy

**Option 4: Add PORT environment variable manually**
1. Go to Railway dashboard → Variables
2. Add: `PORT=8000`
3. Redeploy

### Useful Railway CLI Commands:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# View logs
railway logs

# Run migrations
railway run alembic upgrade head
```

## Cost Estimate
- **Hobby Plan**: $5/month (includes 500 hours, 1GB RAM, 1 vCPU)
- **Pro Plan**: $20/month (includes unlimited hours, 8GB RAM, 8 vCPUs)

## Scaling
Railway automatically handles:
- SSL certificates
- Load balancing
- Health checks
- Auto-restarts
- Monitoring
