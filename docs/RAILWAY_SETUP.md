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

### Database (will be updated with Supabase URL)
```
DATABASE_URL=postgresql://username:password@your-supabase-host:5432/postgres
ASYNC_DATABASE_URL=postgresql+asyncpg://username:password@your-supabase-host:5432/postgres
SYNC_DATABASE_URL=postgresql://username:password@your-supabase-host:5432/postgres
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
GOOGLE_REDIRECT_URI=https://your-railway-app.railway.app/auth/google/callback
```

### Email
```
EMAIL_PROVIDER=postmark
POSTMARK_API_KEY=your-postmark-api-key
```

### Frontend URL (will be updated with Vercel URL)
```
FRONTEND_URL=https://your-vercel-app.vercel.app
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
2. **Port Binding**: Ensure your app binds to `0.0.0.0:$PORT`
3. **Database Connection**: Verify DATABASE_URL format
4. **CORS Issues**: Make sure your frontend domain is allowed

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
