# CoachIntel Production Deployment Guide

## Prerequisites

Before deploying to Vercel, you'll need to set up production infrastructure:

### 1. Production Database (PostgreSQL)
You'll need a production PostgreSQL database. Recommended options:
- **Supabase** (free tier available): https://supabase.com/
- **PlanetScale** (free tier available): https://planetscale.com/
- **Neon** (free tier available): https://neon.tech/
- **Railway** (affordable): https://railway.app/

### 2. Production Redis
For session management and Celery tasks:
- **Upstash Redis** (free tier): https://upstash.com/
- **Redis Cloud** (free tier): https://redis.com/
- **Railway Redis**: https://railway.app/

### 3. Backend Hosting
Your FastAPI backend needs to be hosted separately. Options:
- **Railway** (recommended for Python apps): https://railway.app/
- **Render** (free tier available): https://render.com/
- **DigitalOcean App Platform**: https://www.digitalocean.com/products/app-platform
- **Heroku** (paid): https://heroku.com/

## Deployment Steps

### Step 1: Deploy Backend First

1. Choose a backend hosting provider (Railway recommended)
2. Connect your GitHub repository
3. Set up environment variables for production
4. Deploy the `/backend` directory
5. Note the production backend URL

### Step 2: Set Up Production Services

#### Database Setup (using Supabase as example):
1. Go to https://supabase.com/ and create a new project
2. Get your connection string from Settings > Database
3. Run your Alembic migrations against the production database

#### Redis Setup (using Upstash as example):
1. Go to https://upstash.com/ and create a Redis database
2. Get your Redis URL from the dashboard

### Step 3: Deploy Frontend to Vercel

1. **Push to GitHub**: Make sure your code is pushed to GitHub

2. **Connect to Vercel**:
   - Go to https://vercel.com/
   - Click "New Project"
   - Import your GitHub repository
   - Set the root directory to `frontend`

3. **Configure Environment Variables** in Vercel dashboard:
   ```
   DATABASE_URL=postgresql://username:password@your-supabase-host:5432/postgres
   ASYNC_DATABASE_URL=postgresql+asyncpg://username:password@your-supabase-host:5432/postgres
   SYNC_DATABASE_URL=postgresql://username:password@your-supabase-host:5432/postgres
   
   CELERY_BROKER_URL=redis://your-upstash-redis-url
   CELERY_RESULT_BACKEND=redis://your-upstash-redis-url
   REDIS_URL=redis://your-upstash-redis-url
   REDIS_HOST=your-upstash-host
   REDIS_PORT=6379
   
   NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
   NEXT_PUBLIC_BROWSER_API_URL=https://your-backend-url.railway.app
   
   OPENAI_API_KEY=sk-your-openai-key
   
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GOOGLE_REDIRECT_URI=https://your-backend-url.railway.app/auth/google/callback
   
   FRONTEND_URL=https://your-vercel-app.vercel.app
   
   EMAIL_PROVIDER=postmark
   POSTMARK_API_KEY=your-postmark-key
   
   JWT_SECRET=your-secure-production-jwt-secret
   ```

4. **Update Google OAuth**:
   - Go to Google Cloud Console
   - Update your OAuth app's authorized redirect URIs to include your production backend URL
   - Update authorized JavaScript origins to include your Vercel domain

5. **Deploy**: Vercel will automatically deploy your app

### Step 4: Update CORS Settings

Make sure your backend allows requests from your Vercel domain. Update your backend CORS configuration to include:
- `https://your-vercel-app.vercel.app`

### Step 5: Database Migration

Run your database migrations against the production database:
```bash
# From your backend directory
alembic upgrade head
```

## Security Considerations

1. **Generate New JWT Secret**: Use a secure random string for production
2. **Environment Variables**: Never commit production secrets to git
3. **Database Security**: Use SSL connections for your production database
4. **API Keys**: Rotate keys regularly and use different keys for production

## Monitoring and Maintenance

1. **Logs**: Monitor both Vercel and your backend hosting logs
2. **Database**: Set up database backups
3. **SSL**: Ensure all services use HTTPS
4. **Updates**: Keep dependencies updated

## Troubleshooting

### Common Issues:
1. **CORS Errors**: Check that your backend allows requests from your Vercel domain
2. **Environment Variables**: Verify all required env vars are set in both frontend and backend
3. **Database Connection**: Ensure your production database allows connections from your hosting provider
4. **API Endpoints**: Verify your API URLs are correct and accessible

### Quick Checks:
- Test API endpoints directly in browser
- Check network tab in browser dev tools
- Verify environment variables in deployment logs
- Ensure database is accessible and migrations are applied

## Cost Estimates (Free Tiers)

- **Vercel**: Free for personal projects
- **Supabase**: Free tier includes 500MB database
- **Upstash Redis**: Free tier includes 10K requests/day
- **Railway**: $5/month for backend hosting

Total estimated cost: $5-10/month for a production deployment with room to grow.
