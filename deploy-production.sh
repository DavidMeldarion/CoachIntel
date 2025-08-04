#!/bin/bash

# CoachIntel Production Deployment Helper Script
# This script helps you deploy to Railway, Upstash, Supabase, and Vercel

echo "🚀 CoachIntel Production Deployment Helper"
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the CoachIntel root directory."
    exit 1
fi

echo ""
echo "📋 Pre-deployment Checklist:"
echo ""

# Environment setup check
echo "1. Environment Variables Setup"
echo "   ✓ Copy .env.production and fill in your values"
echo "   ✓ Add environment variables to Railway dashboard"
echo "   ✓ Add environment variables to Vercel dashboard"
echo ""

# Infrastructure check
echo "2. Infrastructure Setup"
echo "   📍 Supabase: Create database at supabase.com"
echo "   📍 Upstash: Create Redis at upstash.com"
echo "   📍 Railway: Deploy backend at railway.app"
echo "   📍 Vercel: Deploy frontend at vercel.com"
echo ""

# Security check
echo "3. Security Configuration"
echo "   🔐 Generate new JWT_SECRET for production"
echo "   🔐 Update Google OAuth redirect URIs"
echo "   🔐 Use HTTPS URLs everywhere"
echo ""

echo "🔧 Quick Commands:"
echo ""
echo "Generate JWT Secret:"
echo "openssl rand -hex 32"
echo ""
echo "Deploy to Railway (if CLI installed):"
echo "railway login && railway link && railway up"
echo ""
echo "Run Database Migration:"
echo "railway run alembic upgrade head"
echo ""
echo "Check Deployment Status:"
echo "railway status"
echo ""

echo "📖 For detailed instructions, see:"
echo "   📄 PRODUCTION_SETUP.md - Complete deployment guide"
echo "   📄 docs/RAILWAY_SETUP.md - Railway configuration"
echo "   📄 docs/SUPABASE_SETUP.md - Database setup"
echo "   📄 docs/UPSTASH_SETUP.md - Redis setup"
echo ""

echo "🎯 Quick Links:"
echo "   🚂 Railway: https://railway.app"
echo "   ⚡ Vercel: https://vercel.com"
echo "   🗄️  Supabase: https://supabase.com"
echo "   📊 Upstash: https://upstash.com"
echo ""

echo "✅ Ready to deploy? Follow the PRODUCTION_SETUP.md guide!"
echo ""

# Optional: Check if required files exist
if [ -f ".env.production" ]; then
    echo "✅ .env.production file found"
else
    echo "⚠️  .env.production file not found - copy and configure it first"
fi

if [ -f "backend/railway.json" ]; then
    echo "✅ Railway configuration found"
else
    echo "⚠️  backend/railway.json not found"
fi

if [ -f "vercel.json" ]; then
    echo "✅ Vercel configuration found"
else
    echo "⚠️  vercel.json not found"
fi

echo ""
echo "🚀 Happy deploying!"
