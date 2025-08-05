# 🚀 CoachIntel Production Deployment Checklist

## Pre-Deployment Setup

### Backend Infrastructure
- [ ] Set up production PostgreSQL database (Supabase/Neon/PlanetScale)
- [ ] Set up production Redis instance (Upstash/Redis Cloud)
- [ ] Deploy backend to hosting provider (Railway/Render/DigitalOcean)
- [ ] Run database migrations: `alembic upgrade head`
- [ ] Test backend API endpoints
- [ ] Configure CORS for production frontend domain

### Frontend Infrastructure
- [ ] Push code to GitHub repository
- [ ] Create Vercel account and connect GitHub repo
- [ ] Set root directory to `frontend` in Vercel

## Environment Variables Configuration

### Required Vercel Environment Variables:
- [ ] `DATABASE_URL` - Production PostgreSQL connection string
- [ ] `ASYNC_DATABASE_URL` - Async PostgreSQL connection string
- [ ] `SYNC_DATABASE_URL` - Sync PostgreSQL connection string
- [ ] `CELERY_BROKER_URL` - Redis URL for Celery
- [ ] `CELERY_RESULT_BACKEND` - Redis URL for results
- [ ] `REDIS_URL` - Redis connection string
- [ ] `REDIS_HOST` - Redis host
- [ ] `REDIS_PORT` - Redis port (usually 6379)
- [ ] `NEXT_PUBLIC_API_URL` - Production backend URL
- [ ] `NEXT_PUBLIC_BROWSER_API_URL` - Production backend URL
- [ ] `OPENAI_API_KEY` - OpenAI API key
- [ ] `GOOGLE_CLIENT_ID` - Google OAuth client ID
- [ ] `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- [ ] `GOOGLE_REDIRECT_URI` - Production backend OAuth callback
- [ ] `FRONTEND_URL` - Vercel app URL
- [ ] `EMAIL_PROVIDER` - postmark
- [ ] `POSTMARK_API_KEY` - Postmark API key
- [ ] `JWT_SECRET` - Secure random string for production

## Security & OAuth Setup

### Google OAuth Configuration:
- [ ] Go to Google Cloud Console
- [ ] Add production backend URL to authorized redirect URIs
- [ ] Add Vercel domain to authorized JavaScript origins
- [ ] Test OAuth flow in production

### Security Checklist:
- [ ] Generate new secure JWT_SECRET for production
- [ ] Verify all API connections use HTTPS
- [ ] Test CORS configuration
- [ ] Verify database uses SSL connections
- [ ] Check that no secrets are committed to git

## Testing & Validation

### Deployment Testing:
- [ ] Deploy frontend to Vercel
- [ ] Test landing page loads correctly
- [ ] Test user registration flow
- [ ] Test user login flow
- [ ] Test dashboard access after login
- [ ] Test API connectivity from frontend
- [ ] Test Google OAuth integration
- [ ] Test session management
- [ ] Verify email functionality (if implemented)

### Performance & Monitoring:
- [ ] Check Vercel deployment logs for errors
- [ ] Monitor backend logs for issues
- [ ] Test site performance and loading speeds
- [ ] Verify all images and assets load correctly
- [ ] Test on mobile devices

## Post-Deployment

### Monitoring Setup:
- [ ] Set up database backup schedule
- [ ] Monitor application logs regularly
- [ ] Set up uptime monitoring (optional)
- [ ] Document production URLs and credentials securely

### Maintenance:
- [ ] Plan for regular dependency updates
- [ ] Set up staging environment for testing changes
- [ ] Document rollback procedures
- [ ] Create maintenance runbook

## Quick Commands

### Deploy to Production:
```bash
# Push changes to trigger deployment
git add .
git commit -m "Deploy to production"
git push origin main
```

### Check Deployment Status:
- Vercel Dashboard: https://vercel.com/dashboard
- Check deployment logs in Vercel
- Monitor backend logs in hosting provider dashboard

### Rollback if Needed:
- Use Vercel dashboard to revert to previous deployment
- Or push a fix commit to trigger new deployment

## Emergency Contacts & Resources

- **Vercel Support**: https://vercel.com/support
- **OpenAI Status**: https://status.openai.com/
- **Google OAuth Console**: https://console.cloud.google.com/
- **Database Provider Support**: [Your chosen provider]
- **Redis Provider Support**: [Your chosen provider]

---

**Note**: Keep this checklist updated as you add new features or change infrastructure.
