#!/bin/bash
# Railway startup script for CoachIntel backend

# Set default port if PORT env var is not set
PORT=${PORT:-8000}

echo "Starting CoachIntel backend on port $PORT"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the FastAPI application
echo "Starting FastAPI application..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT
