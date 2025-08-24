import os
import pytest

# Ensure test database envs are honored if set by test harness
# (conftest will manage skipping if not configured)

def test_health_lazy_worker_endpoint(client):
    resp = client.get('/health/lazy-worker')
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get('status') == 'ok'
    # Celery app should lazy load on first call
    assert data.get('celery_loaded') is True
