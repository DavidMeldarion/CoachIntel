# Upstash Redis Setup Guide for CoachIntel

## Step 1: Create Upstash Account
1. Go to [upstash.com](https://upstash.com)
2. Sign up with GitHub account
3. Verify your email address

## Step 2: Create Redis Database
1. Click "Create Database" in dashboard
2. **Name**: `coachintel-redis`
3. **Type**: Regional (for better performance)
4. **Region**: Choose same region as your Railway backend
5. **Eviction**: allkeys-lru (recommended)
6. Click "Create"

## Step 3: Get Connection Details
After creation, go to database details:

### Connection String:
```
redis://default:YOUR_PASSWORD@your-endpoint.upstash.io:PORT
```

### Individual Components:
- **Host**: `your-endpoint.upstash.io`
- **Port**: `6379` or `6380` (SSL)
- **Password**: Your generated password
- **Username**: `default`

## Step 4: Environment Variables
Use these in Railway backend:

```bash
# Full Redis URL for Celery
CELERY_BROKER_URL=redis://default:YOUR_PASSWORD@your-endpoint.upstash.io:6379
CELERY_RESULT_BACKEND=redis://default:YOUR_PASSWORD@your-endpoint.upstash.io:6379
REDIS_URL=redis://default:YOUR_PASSWORD@your-endpoint.upstash.io:6379

# Individual components
REDIS_HOST=your-endpoint.upstash.io
REDIS_PORT=6379
REDIS_PASSWORD=YOUR_PASSWORD
```

## Step 5: Test Connection
Test Redis connection from Railway:

```python
import redis

# Test connection
r = redis.from_url("redis://default:YOUR_PASSWORD@your-endpoint.upstash.io:6379")
r.ping()  # Should return True
```

## Step 6: Configure for Session Storage
Update your backend Redis configuration:

```python
# In your FastAPI app
import redis
from fastapi import FastAPI

app = FastAPI()

# Redis client for sessions
redis_client = redis.from_url(
    os.getenv("REDIS_URL"),
    decode_responses=True,
    ssl_cert_reqs=None  # For Upstash SSL
)
```

## Upstash Features
- **Serverless**: Pay per request
- **Global**: Multi-region replication
- **REST API**: HTTP-based access
- **Durable**: Persistent storage
- **SSL/TLS**: Secure connections

## Free Tier Limits
- **Storage**: 256MB
- **Requests**: 10,000/day
- **Connections**: 20 concurrent
- **Bandwidth**: 1GB/month

## Production Configuration

### SSL Connection (Recommended):
```bash
REDIS_URL=rediss://default:YOUR_PASSWORD@your-endpoint.upstash.io:6380
```

### Connection Pooling:
```python
import redis

pool = redis.ConnectionPool.from_url(
    os.getenv("REDIS_URL"),
    max_connections=20,
    ssl_cert_reqs=None
)
redis_client = redis.Redis(connection_pool=pool)
```

## Monitoring
1. Go to Upstash dashboard
2. Monitor requests and storage usage
3. Check connection metrics
4. Set up alerts for high usage

## Scaling Options
When you outgrow free tier:
- **Pay-as-you-go**: $0.2 per 100K requests
- **Pro Plans**: Starting at $280/month for dedicated instances

## Use Cases in CoachIntel
1. **Session Storage**: User authentication tokens
2. **Celery Broker**: Background task queue
3. **Caching**: API response caching
4. **Rate Limiting**: API request limits
5. **Real-time Features**: WebSocket connections

## Security Best Practices
1. Use TLS/SSL connections in production
2. Rotate passwords regularly
3. Use VPC peering for additional security
4. Monitor access logs
5. Set up IP allowlists if needed

## Troubleshooting
1. **Connection Timeouts**: Check SSL configuration
2. **Authentication Errors**: Verify password and username
3. **Performance Issues**: Monitor connection pool size
4. **Memory Issues**: Check data expiration policies

## CLI Tools
Install Upstash CLI for management:
```bash
# Install
npm install -g @upstash/cli

# Login
upstash auth login

# List databases
upstash redis list

# Get database info
upstash redis get DATABASE_ID
```

## Backup Strategy
- **Automatic Snapshots**: Available in paid plans
- **Manual Export**: Use Redis DUMP commands
- **Cross-region Replication**: Available in global databases
