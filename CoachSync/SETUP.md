# CoachSync Environment Setup Guide

## Prerequisites
- Docker and Docker Compose
- Git
- Node.js 18+ (for local frontend development)
- Python 3.10+ (for local backend development)

## Initial Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd CoachSync
```

### 2. Environment Configuration

#### Backend Environment
1. Copy the example environment file:
   ```bash
   cp backend/.env.example backend/.env
   ```

2. Update `backend/.env` with your actual values:
   - Set a secure `JWT_SECRET` (generate with: `openssl rand -hex 32`)
   - Configure Google OAuth credentials
   - Set external API keys (Fireflies, Zoom) if needed

#### Frontend Environment
1. Copy the example environment file:
   ```bash
   cp frontend/.env.example frontend/.env.local
   ```

2. Update `frontend/.env.local` with your backend URL (usually `http://localhost:8000`)

### 3. Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   - `http://localhost:8000/auth/google/callback` (for local development)
6. Copy Client ID and Client Secret to `backend/.env`

### 4. Start the Application
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 5. Database Migrations
```bash
# Apply migrations
docker-compose exec backend alembic upgrade head

# Create new migration (if you modify models)
docker-compose exec backend alembic revision --autogenerate -m "description"
```

## Development Workflow

### Hot Reload Development
The Docker setup includes hot reload for both frontend and backend:
- Frontend: Next.js dev server with file watching
- Backend: FastAPI with auto-reload on file changes

### Adding New Dependencies

#### Frontend (Node.js)
```bash
# Enter the container
docker-compose exec frontend bash

# Install packages
npm install <package-name>

# Or from host (will sync with container)
cd frontend
npm install <package-name>
```

#### Backend (Python)
```bash
# Enter the container
docker-compose exec backend bash

# Install packages
pip install <package-name>

# Update requirements.txt
pip freeze > requirements.txt
```

### Database Management

#### Access PostgreSQL
```bash
# Connect to database
docker-compose exec db psql -U user -d coachsync

# View tables
\dt

# Exit
\q
```

#### Redis Management
```bash
# Connect to Redis
docker-compose exec redis redis-cli

# View keys
KEYS *

# Exit
exit
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure PostgreSQL container is running: `docker-compose ps`
   - Check database URL in `.env` files
   - Verify database exists: `docker-compose exec db psql -U user -l`

2. **Google OAuth Issues**
   - Verify redirect URI matches exactly in Google Console
   - Check that GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set
   - Ensure frontend can reach backend API

3. **Frontend Build Errors**
   - Clear Next.js cache: `rm -rf frontend/.next`
   - Reinstall dependencies: `docker-compose exec frontend npm install`

4. **Migration Errors**
   - Check current migration status: `docker-compose exec backend alembic current`
   - View migration history: `docker-compose exec backend alembic history`
   - Reset database (DESTRUCTIVE): `docker-compose down -v && docker-compose up -d`

### Logs and Debugging
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs frontend
docker-compose logs backend
docker-compose logs db

# Follow logs in real-time
docker-compose logs -f backend
```

## Production Deployment

### Environment Variables
- Set `NODE_ENV=production` for frontend
- Set `ENVIRONMENT=production` for backend
- Use secure database credentials
- Use HTTPS URLs for all external endpoints
- Set secure JWT secret (minimum 32 characters)

### Security Checklist
- [ ] All `.env` files are in `.gitignore`
- [ ] Google OAuth redirect URIs use HTTPS in production
- [ ] Database uses SSL/TLS connections
- [ ] JWT secret is cryptographically secure
- [ ] API rate limiting is enabled
- [ ] CORS is properly configured

## File Structure
```
CoachSync/
├── docker-compose.yml          # Multi-service orchestration
├── .gitignore                  # Git ignore rules
├── backend/
│   ├── .env.example           # Backend environment template
│   ├── alembic/               # Database migrations
│   ├── app/                   # FastAPI application
│   └── Dockerfile             # Backend container
├── frontend/
│   ├── .env.example           # Frontend environment template
│   ├── app/                   # Next.js pages and API routes
│   ├── components/            # Reusable React components
│   └── Dockerfile             # Frontend container
└── shared/                    # Shared utilities and types
```
