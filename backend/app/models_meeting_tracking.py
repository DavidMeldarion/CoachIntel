"""Multi-tenant meeting tracking models (SQLAlchemy 2.x style).

Updated: Merged to use existing integer `users.id` primary key (coaches) from `app.models`.
The duplicate UUID `User` model has been removed. All coach references now use INT FK.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    MetaData, Enum as SAEnum, text, ForeignKey, String, DateTime, JSON, func, Index, UniqueConstraint, PrimaryKeyConstraint, Computed
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, CITEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from .models import User  # existing coach/user model (INT PK)

# ---------------------------------------------------------------------------
# Naming conventions (important for Alembic autogenerate stability)
# ---------------------------------------------------------------------------
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

class Base(DeclarativeBase):  # separate base to avoid clashing with existing legacy Base
    metadata = metadata

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
ClientStatusEnum = SAEnum("prospect", "active", "inactive", name="client_status")

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Person(Base):
    __tablename__ = "persons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    primary_email: Mapped[Optional[str]] = mapped_column(CITEXT(), nullable=True)
    primary_phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    emails: Mapped[List[str]] = mapped_column(ARRAY(CITEXT()), server_default=text("'{}'"), nullable=False)
    phones: Mapped[List[str]] = mapped_column(ARRAY(String), server_default=text("'{}'"), nullable=False)
    email_hashes: Mapped[List[str]] = mapped_column(ARRAY(String), server_default=text("'{}'"), nullable=False)
    phone_hashes: Mapped[List[str]] = mapped_column(ARRAY(String), server_default=text("'{}'"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    clients: Mapped[List["Client"]] = relationship(back_populates="person")
    meeting_attendances: Mapped[List["MeetingAttendee"]] = relationship(back_populates="person")

    __table_args__ = (
        Index("ix_person_email_hashes", "email_hashes", postgresql_using="gin"),
        Index("ix_person_phone_hashes", "phone_hashes", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Person id={self.id} primary_email={self.primary_email!r}>"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    person_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(ClientStatusEnum, nullable=False, server_default=text("'prospect'"), index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    coach: Mapped[User] = relationship(back_populates="clients")
    person: Mapped[Person] = relationship(back_populates="clients")

    __table_args__ = (
        UniqueConstraint("coach_id", "person_id", name="uq_clients_coach_person"),
        Index("ix_clients_coach_status", "coach_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Client id={self.id} coach_id={self.coach_id} person_id={self.person_id} status={self.status}>"


class ExternalAccount(Base):
    __tablename__ = "external_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    access_token_enc: Mapped[Optional[bytes]] = mapped_column(String, nullable=True)  # stored base64/fernet string
    refresh_token_enc: Mapped[Optional[bytes]] = mapped_column(String, nullable=True)
    scopes: Mapped[List[str]] = mapped_column(ARRAY(String), server_default=text("'{}'"), nullable=False)
    external_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    coach: Mapped[User] = relationship(back_populates="external_accounts")

    __table_args__ = (
        UniqueConstraint("coach_id", "provider", name="uq_external_accounts_coach_provider"),
        Index("ix_external_accounts_provider", "provider"),
    )

    def __repr__(self) -> str:
        return f"<ExternalAccount id={self.id} provider={self.provider!r} coach_id={self.coach_id}>"


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    join_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ical_uid: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    external_refs: Mapped[dict] = mapped_column(JSON, server_default=text("'{}'::jsonb"), nullable=False)
    transcript_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    coach: Mapped[User] = relationship(back_populates="meetings")
    attendees: Mapped[List["MeetingAttendee"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_meeting_ical_uid", "ical_uid"),  # duplicate of inline index but explicit naming
        Index("ix_meeting_zoom_meeting_id", text("(external_refs ->> 'zoom_meeting_id')")),
        Index("ix_meetings_coach_started", "coach_id", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<Meeting id={self.id} coach_id={self.coach_id} started_at={self.started_at}>"


class MeetingAttendee(Base):
    __tablename__ = "meeting_attendees"

    meeting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="SET NULL"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    external_attendee_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_email: Mapped[Optional[str]] = mapped_column(CITEXT(), nullable=True)
    raw_phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Generated identity key replicating COALESCE(external_attendee_id, raw_email, raw_name)
    identity_key: Mapped[str] = mapped_column(
        String,
        Computed("COALESCE(external_attendee_id, raw_email, raw_name)", persisted=True),
        nullable=False,
    )

    meeting: Mapped[Meeting] = relationship(back_populates="attendees")
    person: Mapped[Optional[Person]] = relationship(back_populates="meeting_attendances")

    __table_args__ = (
        PrimaryKeyConstraint("meeting_id", "source", "identity_key", name="pk_meeting_attendee"),
        Index("ix_meeting_attendees_meeting_source", "meeting_id", "source"),
    )

    def __repr__(self) -> str:
        return (
            f"<MeetingAttendee meeting_id={self.meeting_id} source={self.source} "
            f"identity_key={getattr(self, 'identity_key', None)!r}>"
        )


class ReviewCandidate(Base):
    """Potential person merge / identity conflict candidates for manual review.

    Records two person IDs that might represent the same real-world individual along with
    the triggering context (meeting / attendee / reason).
    """
    __tablename__ = "review_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    person_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    person_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    meeting_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("coach_id", "person_a_id", "person_b_id", "meeting_id", name="uq_review_candidate_pair"),
        Index("ix_review_candidates_coach_created", "coach_id", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - repr utility
        return f"<ReviewCandidate coach_id={self.coach_id} a={self.person_a_id} b={self.person_b_id} resolved={self.resolved}>"


# ---------------------------------------------------------------------------
# Extension requirements note: ensure 'citext' extension exists (Alembic migration).
# ---------------------------------------------------------------------------
# Example Alembic snippet (NOT executed here):
#   op.execute("CREATE EXTENSION IF NOT EXISTS citext")
# ---------------------------------------------------------------------------
