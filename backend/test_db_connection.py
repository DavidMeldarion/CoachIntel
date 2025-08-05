#!/usr/bin/env python3
"""
Test database connectivity for Railway deployment
"""
import os
import asyncio
import asyncpg
import psycopg2
from urllib.parse import urlparse

async def test_async_connection():
    """Test async database connection"""
    async_url = os.getenv("ASYNC_DATABASE_URL")
    if not async_url:
        print("❌ ASYNC_DATABASE_URL not set")
        return False
    
    try:
        # Parse URL to remove the postgresql+asyncpg:// prefix for asyncpg
        parsed = urlparse(async_url)
        clean_url = async_url.replace("postgresql+asyncpg://", "postgresql://")
        
        print(f"🔍 Testing async connection to: {parsed.hostname}")
        conn = await asyncpg.connect(clean_url)
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        
        if result == 1:
            print("✅ Async connection successful!")
            return True
    except Exception as e:
        print(f"❌ Async connection failed: {e}")
        return False

def test_sync_connection():
    """Test sync database connection"""
    sync_url = os.getenv("DATABASE_URL") or os.getenv("SYNC_DATABASE_URL")
    if not sync_url:
        print("❌ DATABASE_URL not set")
        return False
    
    try:
        parsed = urlparse(sync_url)
        print(f"🔍 Testing sync connection to: {parsed.hostname}")
        
        conn = psycopg2.connect(sync_url)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result and result[0] == 1:
            print("✅ Sync connection successful!")
            return True
    except Exception as e:
        print(f"❌ Sync connection failed: {e}")
        return False

async def main():
    print("🚀 Testing CoachIntel Database Connections")
    print("=" * 50)
    
    # Test sync connection
    sync_ok = test_sync_connection()
    
    # Test async connection
    async_ok = await test_async_connection()
    
    print("=" * 50)
    if sync_ok and async_ok:
        print("🎉 All database connections working!")
        return True
    else:
        print("💥 Some connections failed. Check your environment variables.")
        return False

if __name__ == "__main__":
    asyncio.run(main())
