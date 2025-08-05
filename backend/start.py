#!/usr/bin/env python3
"""
Railway startup script for CoachIntel backend
This script handles the PORT environment variable properly and runs migrations
"""
import os
import subprocess
import sys

def main():
    # Get port from environment variable, default to 8000
    port = os.environ.get('PORT', '8000')
    
    print(f"Starting CoachIntel backend on port {port}")
    
    # Run database migrations
    print("Running database migrations...")
    try:
        subprocess.run(['alembic', 'upgrade', 'head'], check=True)
        print("Database migrations completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Migration failed: {e}")
        print("Continuing with startup (migrations may not be needed)")
    
    # Start the FastAPI application
    print("Starting FastAPI application...")
    cmd = [
        'uvicorn',
        'app.main:app',
        '--host', '0.0.0.0',
        '--port', str(port)
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    os.execvp('uvicorn', cmd)

if __name__ == '__main__':
    main()
