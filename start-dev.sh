#!/bin/bash

# Quick start script for CoachIntel development

echo "🚀 Starting CoachIntel Development Environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the CoachIntel root directory."
    exit 1
fi

# Start the development environment
echo "📦 Starting Docker containers..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
docker-compose ps

echo "✅ Development environment is ready!"
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 Backend Docs: http://localhost:8000/docs"
echo ""
echo "📝 To view logs: docker-compose logs -f"
echo "🛑 To stop: docker-compose down"
