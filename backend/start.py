#!/usr/bin/env python3
"""
Railway startup script for CoachIntel backend
This script can start:
- API server (default): python start.py api
- Celery worker:        python start.py worker
- Celery beat:          python start.py beat
"""
import os
import subprocess
import sys
from urllib.parse import urlparse


def mask_redis_url(url: str) -> str:
    try:
        if not url:
            return ""
        p = urlparse(url)
        if p.password:
            return url.replace(p.password, "****")
        return url
    except Exception:
        return "****"


def run_api() -> None:
    port = os.environ.get("PORT", "8000")
    print(f"Starting CoachIntel backend (API) on port {port}")

    # Run database migrations (best-effort)
    print("Running database migrations...")
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        print("Database migrations completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Migration failed: {e}; continuing startup")

    # Start FastAPI via uvicorn
    cmd = [
        "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
    ]
    print(f"Running command: {' '.join(cmd)}")
    os.execvp("uvicorn", cmd)


def run_worker() -> None:
    redis_url = os.environ.get("REDIS_URL") or os.environ.get("UPSTASH_REDIS_URL") or ""
    print(f"Starting Celery worker; REDIS_URL={mask_redis_url(redis_url)}")
    # Use solo pool for serverless environments
    loglevel = os.environ.get("CELERY_LOG_LEVEL", "info")
    cmd = [
        "celery",
        "-A", "app.worker.celery_app",
        "worker",
        "--loglevel", loglevel,
        "--pool", "solo",
    ]
    print(f"Running command: {' '.join(cmd)}")
    os.execvp("celery", cmd)


def run_beat() -> None:
    redis_url = os.environ.get("REDIS_URL") or os.environ.get("UPSTASH_REDIS_URL") or ""
    print(f"Starting Celery beat; REDIS_URL={mask_redis_url(redis_url)}")
    loglevel = os.environ.get("CELERY_LOG_LEVEL", "info")
    cmd = [
        "celery",
        "-A", "app.worker.celery_app",
        "beat",
        "--loglevel", loglevel,
    ]
    print(f"Running command: {' '.join(cmd)}")
    os.execvp("celery", cmd)


def main():
    role = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SERVICE_ROLE", "api")).lower()
    if role == "api":
        run_api()
    elif role == "worker":
        run_worker()
    elif role == "beat":
        run_beat()
    else:
        print(f"Unknown role '{role}'. Use one of: api, worker, beat")
        sys.exit(1)


if __name__ == "__main__":
    main()
