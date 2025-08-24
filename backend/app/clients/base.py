from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Any, Iterable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models_meeting_tracking import ExternalAccount
from app.utils.crypto import fernet
from app.services.oauth import refresh_if_needed, OAuthError
import logging, datetime as dt

logger = logging.getLogger("ext_clients")

class TokenSourceError(Exception):
    pass

@dataclass
class AccessToken:
    token: str
    expires_at: int | None = None  # unix seconds
    refresh_token: str | None = None
    scopes: list[str] | None = None

class ExternalAPIClient(Protocol):
    async def _ensure_token(self) -> AccessToken: ...

async def fetch_account(session: AsyncSession, coach_id: int, provider: str) -> ExternalAccount | None:
    stmt = select(ExternalAccount).where(ExternalAccount.coach_id==coach_id, ExternalAccount.provider==provider)
    return (await session.execute(stmt)).scalar_one_or_none()

class OAuthExternalClient:
    provider: str
    coach_id: int
    session: AsyncSession
    account: ExternalAccount | None
    _cached: AccessToken | None

    def __init__(self, session: AsyncSession, coach_id: int, provider: str):
        self.session = session
        self.coach_id = coach_id
        self.provider = provider
        self.account = None
        self._cached = None

    async def _load_account(self) -> ExternalAccount | None:
        if not self.account:
            self.account = await fetch_account(self.session, self.coach_id, self.provider)
        return self.account

    async def _ensure_token(self) -> AccessToken:
        if self._cached and (self._cached.expires_at is None or self._cached.expires_at - 120 > int(dt.datetime.utcnow().timestamp())):
            return self._cached
        acct = await self._load_account()
        if not acct or not acct.access_token_enc:
            raise TokenSourceError(f"No external account for provider={self.provider} coach={self.coach_id}")
        f = fernet()
        try:
            access = f.decrypt(acct.access_token_enc.encode()).decode()
        except Exception:
            raise TokenSourceError("Cannot decrypt access token")
        exp_ts = int(acct.expires_at.timestamp()) if acct.expires_at else None
        refresh_plain = None
        if acct.refresh_token_enc:
            try:
                refresh_plain = f.decrypt(acct.refresh_token_enc.encode()).decode()
            except Exception:
                refresh_plain = None
        if refresh_plain and exp_ts:
            try:
                upd = refresh_if_needed(self.provider, refresh_plain, exp_ts)
                if upd:
                    access = upd['access_token']
                    acct.access_token_enc = f.encrypt(access.encode()).decode()
                    if upd.get('refresh_token') and upd['refresh_token'] != refresh_plain:
                        acct.refresh_token_enc = f.encrypt(upd['refresh_token'].encode()).decode()
                    acct.expires_at = dt.datetime.utcfromtimestamp(upd['expires_at']).replace(tzinfo=dt.timezone.utc)
                    acct.scopes = upd.get('scopes') or acct.scopes
                    await self.session.flush()
                    exp_ts = upd['expires_at']
            except OAuthError as e:
                logger.warning("Token refresh failed for %s coach=%s: %s", self.provider, self.coach_id, e)
        self._cached = AccessToken(token=access, expires_at=exp_ts, refresh_token=refresh_plain, scopes=acct.scopes if acct else None)
        return self._cached
