# Supabase Database Setup Guide for CoachIntel

## Step 1: Create Supabase Account
1. Go to [supabase.com](https://supabase.com)
2. Sign up with GitHub account
3. Click "New Project"

## Step 2: Project Configuration
1. **Organization**: Use your default organization
2. **Project Name**: `coachintel-production`
3. **Database Password**: Generate a strong password (save it!)
4. **Region**: Choose closest to your users
5. **Pricing Plan**: Start with Free tier

## Step 3: Get Connection Details
After project creation, go to Settings > Database:

### Connection String Format:
```
postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
```

### For AsyncPG (Python async):
```
postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
```

## Step 4: Configure Database Access (IMPORTANT)
1. Go to Settings > Database
2. Scroll to "Connection Pooling"
3. **ENABLE connection pooling** - This is essential for production
4. **Copy the pooler connection string** (this is what you'll use in production)
5. The pooler URL format: `postgresql://postgres.PROJECT_REF:PASSWORD@REGION.pooler.supabase.com:6543/postgres`

## Step 5: Security Configuration
1. Go to Authentication > Settings
2. Configure site URL: `https://your-vercel-app.vercel.app`
3. Set redirect URLs for OAuth

## Step 6: Environment Variables
**IMPORTANT: Use Connection Pooler URLs for Production**

```bash
# Use POOLER URLs (from Connection Pooling section in Supabase)
# Format: postgresql://postgres.PROJECT_REF:PASSWORD@REGION.pooler.supabase.com:6543/postgres

# Direct connection (for migrations and admin tasks)
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@REGION.pooler.supabase.com:6543/postgres

# Async connection (for FastAPI app)
ASYNC_DATABASE_URL=postgresql+asyncpg://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@REGION.pooler.supabase.com:6543/postgres

# Sync connection (for Alembic migrations)
SYNC_DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@REGION.pooler.supabase.com:6543/postgres
```

**Note**: 
- Use **port 6543** for pooler connections (not 5432)
- The hostname format is different: `REGION.pooler.supabase.com`
- This prevents "Network unreachable" errors on Railway and other hosting platforms

## Step 7: Run Database Migrations
After Railway deployment, run migrations:

```bash
# Connect to Railway and run migrations
railway run alembic upgrade head
```

## Step 8: Verify Database Setup
1. Check tables are created in Supabase dashboard
2. Go to Table Editor to view your tables
3. Test connection from your Railway backend

## Supabase Features You Can Use Later
- **Authentication**: Built-in auth system
- **Real-time**: Live data updates
- **Storage**: File storage for audio files
- **Edge Functions**: Serverless functions
- **API**: Auto-generated REST API

## Free Tier Limits
- **Database**: 500MB storage
- **Bandwidth**: 2GB
- **API Requests**: 50,000/month
- **Authentication**: 50,000 monthly active users

## Monitoring
1. Go to Reports in Supabase dashboard
2. Monitor database usage
3. Set up alerts for high usage
4. Check query performance

## Backup Strategy
1. **Automatic Backups**: Included in paid plans
2. **Manual Backup**: Use pg_dump
3. **Point-in-time Recovery**: Available in paid plans

## Scaling Options
When you outgrow free tier:
- **Pro Plan**: $25/month (8GB database, 100GB bandwidth)
- **Team Plan**: $599/month (120GB database, 250GB bandwidth)

## Security Best Practices
1. Use Row Level Security (RLS) policies
2. Enable SSL-only connections
3. Regularly rotate database passwords
4. Monitor connection logs
5. Set up IP restrictions if needed

## Connection Troubleshooting
1. **Timeout Issues**: Check connection pooling settings
2. **SSL Errors**: Ensure SSL is enabled in connection string
3. **Permission Errors**: Verify user has correct permissions
4. **Performance**: Use connection pooling for high traffic
