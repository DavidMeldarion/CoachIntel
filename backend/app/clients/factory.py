from __future__ import annotations
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession
from .google_calendar_client import GoogleCalendarClient
from .zoom_client import ZoomClient
from .calendly_client import CalendlyClient
from .fireflies_client import FirefliesClient

Provider = Literal['google','zoom','calendly','fireflies']

async def get_client(session: AsyncSession, coach_id: int, provider: Provider):
    p = provider.lower()
    if p == 'google':
        return GoogleCalendarClient(session, coach_id)
    if p == 'zoom':
        return ZoomClient(session, coach_id)
    if p == 'calendly':
        return CalendlyClient(session, coach_id)
    if p == 'fireflies':
        return FirefliesClient(session, coach_id)
    raise ValueError(f"Unsupported provider {provider}")
