"""OAuth helper utilities for multiple providers (google, zoom, calendly, fireflies).

Supports:
 - build_auth_url(provider, coach_id, state?) -> str
 - exchange_code(provider, code) -> token dict (access_token, refresh_token?, expires_at, scopes, external_user_id)
 - refresh_if_needed(provider, account) -> updated fields if refresh occurs

Tokens are stored encrypted (fernet) by caller; this module returns plaintext tokens.
"""
from __future__ import annotations

import os, time, base64
from typing import Dict, Any, Optional, List
import httpx

PROVIDERS = {"google", "zoom", "calendly", "fireflies"}


class OAuthError(RuntimeError):
    pass


def _env(name: str, required: bool = True) -> Optional[str]:
    val = os.getenv(name)
    if required and not val:
        raise OAuthError(f"Missing env var {name}")
    return val


def provider_config(provider: str) -> Dict[str, Any]:
    p = provider.lower()
    if p not in PROVIDERS:
        raise OAuthError(f"Unsupported provider {provider}")
    if p == "google":
        return {
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "client_id": _env("GOOGLE_CLIENT_ID"),
            "client_secret": _env("GOOGLE_CLIENT_SECRET"),
            "scopes": ["https://www.googleapis.com/auth/calendar.readonly", "openid", "email", "profile"],
            "redirect_uri": _env("GOOGLE_OAUTH_REDIRECT_URI", required=False) or (_env("OAUTH_REDIRECT_BASE") + "/oauth/google/callback"),
            "response_type": "code",
            "extra_params": {"access_type": "offline", "prompt": "consent"},
        }
    if p == "zoom":
        return {
            "auth_url": "https://zoom.us/oauth/authorize",
            "token_url": "https://zoom.us/oauth/token",
            "client_id": _env("OAUTH_ZOOM_CLIENT_ID"),
            "client_secret": _env("OAUTH_ZOOM_CLIENT_SECRET"),
            "scopes": ["meeting:read", "user:read"],
            "redirect_uri": _env("OAUTH_ZOOM_REDIRECT_URI", required=False) or (_env("OAUTH_REDIRECT_BASE") + "/oauth/zoom/callback"),
            "response_type": "code",
            "extra_params": {},
        }
    if p == "calendly":
        return {
            "auth_url": "https://auth.calendly.com/oauth/authorize",
            "token_url": "https://auth.calendly.com/oauth/token",
            "client_id": _env("CALENDLY_CLIENT_ID"),
            "client_secret": _env("CALENDLY_CLIENT_SECRET"),
            "scopes": ["default"],
            "redirect_uri": _env("CALENDLY_REDIRECT_URI", required=False) or (_env("OAUTH_REDIRECT_BASE") + "/oauth/calendly/callback"),
            "response_type": "code",
            "extra_params": {},
        }
    if p == "fireflies":
        return {
            "auth_url": "https://api.fireflies.ai/oauth/authorize",
            "token_url": "https://api.fireflies.ai/oauth/token",
            "client_id": _env("FIREFLIES_CLIENT_ID"),
            "client_secret": _env("FIREFLIES_CLIENT_SECRET"),
            "scopes": ["meetings.read"],
            "redirect_uri": _env("FIREFLIES_REDIRECT_URI", required=False) or (_env("OAUTH_REDIRECT_BASE") + "/oauth/fireflies/callback"),
            "response_type": "code",
            "extra_params": {},
        }
    raise OAuthError("Unhandled provider")


def build_auth_url(provider: str, coach_id: int, state: str | None = None) -> str:
    cfg = provider_config(provider)
    import urllib.parse
    if not state:
        state = base64.urlsafe_b64encode(f"coach:{coach_id}:{int(time.time())}".encode()).decode().rstrip("=")
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": cfg["response_type"],
        "scope": " ".join(cfg["scopes"]),
        "state": state,
        **cfg.get("extra_params", {}),
    }
    return cfg["auth_url"] + "?" + urllib.parse.urlencode(params)


def exchange_code(provider: str, code: str, redirect_uri: str | None = None) -> Dict[str, Any]:
    cfg = provider_config(provider)
    token_url = cfg["token_url"]
    redirect = redirect_uri or cfg["redirect_uri"]
    auth = (cfg["client_id"], cfg["client_secret"]) if provider == "zoom" else None
    data = {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect,
    }
    headers = {"Accept": "application/json"}
    if provider == "zoom":
        data.pop("client_secret", None)
    resp = httpx.post(token_url, data=data, auth=auth, headers=headers, timeout=15.0)
    if resp.status_code >= 400:
        raise OAuthError(f"Token exchange failed ({resp.status_code}): {resp.text}")
    tok = resp.json()
    access_token = tok.get("access_token")
    if not access_token:
        raise OAuthError("Missing access_token in response")
    refresh_token = tok.get("refresh_token")
    expires_in = tok.get("expires_in") or tok.get("expires") or 3600
    external_user_id = tok.get("user_id") or tok.get("owner_id") or tok.get("resource_owner_id")
    scopes_raw = tok.get("scope") or tok.get("scopes") or ""
    if isinstance(scopes_raw, str):
        scopes_list = [s for s in scopes_raw.replace(",", " ").split() if s]
    else:
        scopes_list = scopes_raw or []
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": int(time.time()) + int(expires_in),
        "scopes": scopes_list,
        "external_user_id": external_user_id,
    }


def refresh_if_needed(provider: str, refresh_token: str, expires_at: int):
    if expires_at - int(time.time()) > 300:
        return None
    cfg = provider_config(provider)
    token_url = cfg["token_url"]
    auth = (cfg["client_id"], cfg["client_secret"]) if provider == "zoom" else None
    data = {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    if provider == "zoom":
        data.pop("client_secret", None)
    resp = httpx.post(token_url, data=data, auth=auth, timeout=15.0)
    if resp.status_code >= 400:
        raise OAuthError(f"Refresh failed: {resp.status_code} {resp.text}")
    tok = resp.json()
    return {
        "access_token": tok.get("access_token"),
        "refresh_token": tok.get("refresh_token", refresh_token),
        "expires_at": int(time.time()) + int(tok.get("expires_in") or 3600),
        "scopes": (tok.get("scope") or "").split(),
    }

__all__ = [
    'build_auth_url', 'exchange_code', 'refresh_if_needed', 'OAuthError'
]
