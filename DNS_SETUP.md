# DNS Configuration Guide for CoachIntel

## Custom Domain Setup

### Recommended Architecture
- **Frontend (Vercel)**: `yourdomain.com` and `www.yourdomain.com`
- **Backend API (Railway)**: `api.yourdomain.com`

### DNS Records Setup in Namecheap

#### For Railway Backend API:
```
Type: CNAME
Name: api
Value: pqy11fu7.up.railway.app
TTL: 300
```

#### For Vercel Frontend:
```
Type: A
Name: @
Value: 76.76.19.19
TTL: 300

Type: A
Name: www  
Value: 76.76.19.19
TTL: 300

Type: AAAA
Name: @
Value: 2606:4700:10::6816:1313
TTL: 300

Type: AAAA
Name: www
Value: 2606:4700:10::6816:1313
TTL: 300
```

### Environment Variables Update

After setting up your custom domains, update your Vercel environment variables:

```env
NEXT_PUBLIC_BROWSER_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### Domain Configuration in Platforms

#### Railway Dashboard:
1. Go to your project → Settings → Domains
2. Add `api.yourdomain.com`
3. Wait for Railway to verify the domain

#### Vercel Dashboard:
1. Go to your project → Settings → Domains  
2. Add `yourdomain.com`
3. Add `www.yourdomain.com`
4. Follow Vercel's verification steps

### Troubleshooting

#### Common Issues:

1. **"CNAME @ not allowed"**: 
   - This is normal - use the subdomain approach above
   - Root domain CNAME conflicts with other DNS records

2. **DNS not propagating**:
   - Wait 24-48 hours for full propagation
   - Check multiple locations: https://whatsmydns.net/
   - Clear local DNS cache: `ipconfig /flushdns`

3. **SSL Certificate issues**:
   - Both Railway and Vercel auto-generate SSL certificates
   - May take a few hours after DNS propagation

#### Testing Your Setup:
```bash
# Test Railway API domain
curl https://api.yourdomain.com/health

# Test Vercel frontend domain  
curl https://yourdomain.com
```

### Why This Setup Works:

- ✅ **No DNS conflicts**: Uses subdomain for Railway API
- ✅ **SEO friendly**: Main domain points to your frontend
- ✅ **SSL automatic**: Both platforms handle certificates
- ✅ **Scalable**: Can easily add more API subdomains later
