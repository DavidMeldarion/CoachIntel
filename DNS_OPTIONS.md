# DNS Configuration Options for Railway + Vercel

## Option 1: Subdomain for Railway (RECOMMENDED)

### Setup:
- **Frontend**: `yourdomain.com` and `www.yourdomain.com` → Vercel
- **Backend API**: `api.yourdomain.com` → Railway

### DNS Records:
```
# Vercel Frontend
Type: A
Name: @  
Value: 76.76.19.19

Type: CNAME
Name: www
Value: cname.vercel-dns.com

# Railway Backend
Type: CNAME  
Name: api
Value: pqy11fu7.up.railway.app
```

### Pros:
- ✅ No DNS conflicts
- ✅ Clean separation of concerns
- ✅ Easy to troubleshoot
- ✅ Industry standard approach

### Environment Variables:
```env
NEXT_PUBLIC_BROWSER_API_URL=https://api.yourdomain.com
```

---

## Option 2: Railway Root + Vercel www

### Setup:
- **Backend**: `yourdomain.com` → Railway  
- **Frontend**: `www.yourdomain.com` → Vercel

### DNS Records:
```
# Railway Backend (root)
Type: CNAME
Name: @
Value: pqy11fu7.up.railway.app

# Vercel Frontend (www)
Type: CNAME
Name: www  
Value: cname.vercel-dns.com
```

### Pros:
- ✅ API at root domain (shorter URLs)
- ✅ Both services get custom domains

### Cons:
- ❌ Users must remember to use www for frontend
- ❌ SEO implications (need redirects)

---

## Option 3: Vercel-Only with Rewrites (ELEGANT)

### Setup:
- **Everything**: `yourdomain.com` → Vercel
- **API Calls**: Proxied to Railway via Next.js rewrites

### DNS Records:
```
# Vercel Only
Type: A
Name: @
Value: 76.76.19.19

Type: CNAME
Name: www
Value: cname.vercel-dns.com
```

### Code Changes:
- Updated `next.config.js` with rewrites
- Updated `apiUrl.ts` to use relative paths in production

### Pros:
- ✅ Single domain to manage
- ✅ Seamless user experience
- ✅ No CORS issues
- ✅ Railway runs without custom domain

### Cons:
- ❌ All API traffic goes through Vercel
- ❌ Slightly more complex setup

---

## Recommended Implementation

**Go with Option 1** (subdomain approach) because:

1. **Simplest setup** - No code changes needed
2. **Most reliable** - No proxy layer
3. **Best performance** - Direct connection to Railway
4. **Industry standard** - APIs commonly use subdomains

### Next Steps for Option 1:

1. **Update DNS in Namecheap:**
   ```
   DELETE: @ CNAME pqy11fu7.up.railway.app
   ADD: api CNAME pqy11fu7.up.railway.app
   ADD: @ A 76.76.19.19
   ADD: www CNAME cname.vercel-dns.com
   ```

2. **Update Railway domain:**
   - Remove root domain
   - Add `api.yourdomain.com`

3. **Update Vercel environment variables:**
   ```env
   NEXT_PUBLIC_BROWSER_API_URL=https://api.yourdomain.com
   ```

4. **Test after DNS propagation:**
   ```bash
   curl https://api.yourdomain.com/health
   curl https://yourdomain.com
   ```
