# CoachIntel Production Deployment Guide
# Complete setup for Railway + Upstash + Supabase + Vercel

## 🚀 Quick Deployment Steps

### Phase 1: Infrastructure Setup (15 minutes)

#### 1. Supabase Database (5 minutes)
1. Go to [supabase.com](https://supabase.com) → Sign up → New Project
2. Name: `coachintel-production`
3. Choose region, generate strong password
4. Wait for project creation
5. Go to Settings → Database → Copy connection string
6. Save the connection details:
   ```
   Host: db.YOUR_PROJECT_REF.supabase.co
   Password: YOUR_PASSWORD
   Database: postgres
   Port: 5432
   ```

#### 2. Upstash Redis (5 minutes)
1. Go to [upstash.com](https://upstash.com) → Sign up → Create Database
2. Name: `coachintel-redis`
3. Type: Regional (same region as Supabase)
4. Copy connection details:
   ```
   Endpoint: your-endpoint.upstash.io
   Port: 6379
   Password: YOUR_REDIS_PASSWORD
   ```

#### 3. Railway Backend (5 minutes)
1. Go to [railway.app](https://railway.app) → Sign up → New Project
2. Deploy from GitHub repo → Select CoachIntel
3. Set root directory: `/backend`
4. Railway auto-detects Python and deploys
5. Note your Railway URL: `your-app.railway.app`

### Phase 2: Environment Configuration (10 minutes)

#### Railway Environment Variables
Add these in Railway dashboard → Variables:

```bash
# Database (replace with your Supabase CONNECTION POOLER details - IMPORTANT!)
# Get these from Supabase Dashboard → Settings → Database → Connection Pooling
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@REGION.pooler.supabase.com:6543/postgres
ASYNC_DATABASE_URL=postgresql+asyncpg://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@REGION.pooler.supabase.com:6543/postgres
SYNC_DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@REGION.pooler.supabase.com:6543/postgres

# Redis (replace with your Upstash details)
CELERY_BROKER_URL=redis://default:YOUR_REDIS_PASSWORD@your-endpoint.upstash.io:6379
CELERY_RESULT_BACKEND=redis://default:YOUR_REDIS_PASSWORD@your-endpoint.upstash.io:6379
REDIS_URL=redis://default:YOUR_REDIS_PASSWORD@your-endpoint.upstash.io:6379
REDIS_HOST=your-endpoint.upstash.io
REDIS_PORT=6379

# API Keys (use your existing values)
OPENAI_API_KEY=your-openai-api-key
JWT_SECRET=generate-new-secure-secret-for-production
POSTMARK_API_KEY=your-postmark-api-key
EMAIL_PROVIDER=postmark

# Google OAuth (update redirect URI)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-railway-app.railway.app/auth/google/callback

# Frontend URL (will update after Vercel deployment)
FRONTEND_URL=https://your-vercel-app.vercel.app
```

#### Run Database Migration
1. Railway dashboard → your service → Deploy tab
2. Click on latest deployment → View Logs
3. Or use Railway CLI:
   ```bash
   npx @railway/cli login
   npx @railway/cli link
   npx @railway/cli run alembic upgrade head
   ```

### Phase 3: Frontend Deployment (5 minutes)

#### Vercel Deployment
1. Go to [vercel.com](https://vercel.com) → Sign up → New Project
2. Import from GitHub → Select CoachIntel repository
3. Framework: Next.js
4. Root Directory: `frontend`
5. Add environment variables:

```bash
# API URLs (replace with your Railway URL)
NEXT_PUBLIC_API_URL=https://your-railway-app.railway.app
NEXT_PUBLIC_BROWSER_API_URL=https://your-railway-app.railway.app

# Google OAuth (same as Railway)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# JWT Secret (same as Railway)
JWT_SECRET=your-secure-jwt-secret

# Database (same as Railway)
DATABASE_URL=postgresql://postgres:YOUR_SUPABASE_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
```

6. Deploy → Note your Vercel URL: `your-app.vercel.app`

### Phase 4: Final Configuration (5 minutes)

#### Update Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. APIs & Services → Credentials → Your OAuth 2.0 Client
3. Add to Authorized JavaScript origins:
   - `https://your-vercel-app.vercel.app`
4. Add to Authorized redirect URIs:
   - `https://your-railway-app.railway.app/auth/google/callback`

#### Update Frontend URL in Railway
1. Railway dashboard → Variables
2. Update `FRONTEND_URL=https://your-vercel-app.vercel.app`
3. Redeploy backend

## 🧪 Testing Your Deployment

### 1. Basic Functionality
- [ ] Visit your Vercel URL
- [ ] Landing page loads correctly
- [ ] Click "Request Early Access" → Sign up form works
- [ ] Test user registration
- [ ] Test Google OAuth login
- [ ] Access dashboard after login

### 2. API Connectivity
- [ ] Check browser network tab for API calls
- [ ] Test: `https://your-railway-app.railway.app/docs` (FastAPI docs)
- [ ] Verify database connection in Railway logs
- [ ] Check Redis connection in Railway logs

### 3. Production Checklist
- [ ] All HTTPS connections working
- [ ] No CORS errors in browser console
- [ ] Database tables created (check Supabase)
- [ ] Email functionality working (if configured)
- [ ] Session persistence working
- [ ] Mobile responsiveness

## 💰 Cost Breakdown

### Free Tier (Perfect for MVP testing):
- **Vercel**: Free
- **Supabase**: Free (500MB database)
- **Upstash**: Free (10K requests/day)
- **Railway**: $5/month (500 hours)
- **Total**: $5/month

### Growth Tier (Production ready):
- **Vercel**: Free (still sufficient)
- **Supabase**: $25/month (8GB database)
- **Upstash**: $280/month (dedicated)
- **Railway**: $20/month (unlimited hours)
- **Total**: $325/month

## 🔧 Maintenance & Monitoring

### Daily Checks:
- Monitor Railway deployment logs
- Check Vercel deployment status
- Monitor Supabase database usage

### Weekly Tasks:
- Review error logs
- Check performance metrics
- Monitor resource usage

### Monthly Tasks:
- Review and rotate secrets
- Update dependencies
- Backup critical data
- Review cost optimization

## 🆘 Troubleshooting Common Issues

### "CORS Error" in browser:
- Check FRONTEND_URL is correct in Railway
- Verify API_URL is correct in Vercel
- Check Railway logs for CORS middleware

### "Database Connection Error":
- Verify DATABASE_URL format in Railway
- Check Supabase connection pooling
- Run migration if tables missing

### "Redis Connection Failed":
- Verify REDIS_URL format
- Check Upstash database status
- Test connection from Railway logs

### "OAuth Error":
- Check Google Cloud Console redirect URIs
- Verify GOOGLE_CLIENT_ID matches
- Check callback URL format

## 📞 Support Resources

- **Railway**: [docs.railway.app](https://docs.railway.app)
- **Vercel**: [vercel.com/docs](https://vercel.com/docs)
- **Supabase**: [supabase.com/docs](https://supabase.com/docs)
- **Upstash**: [docs.upstash.com](https://docs.upstash.com)

---

**🎉 Congratulations!** Your CoachIntel application should now be live in production!
