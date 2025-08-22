"""
Backfill org_id on existing meetings and transcripts by joining to the user's org_id.
Run once after deploying org support and running migrations.

Usage (inside backend container from /app):
  python -m scripts.backfill_org_ids
"""
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.models import sync_engine, User, Meeting, Transcript


def backfill_org_ids():
    with Session(sync_engine) as session:
        # 1) Users with org_id set
        users = session.execute(select(User).where(User.org_id.isnot(None))).scalars().all()
        count_meetings = 0
        count_transcripts = 0
        for u in users:
            # Set org_id on meetings for this user where missing
            m_updated = session.execute(
                update(Meeting)
                .where(Meeting.user_id == u.id, Meeting.org_id.is_(None))
                .values(org_id=u.org_id)
                .returning(Meeting.id)
            ).fetchall()
            count_meetings += len(m_updated)

            # Set org_id on transcripts for this user's meetings where missing
            t_updated = session.execute(
                update(Transcript)
                .where(Transcript.org_id.is_(None))
                .where(Transcript.meeting_id.in_(
                    select(Meeting.id).where(Meeting.user_id == u.id)
                ))
                .values(org_id=u.org_id)
                .returning(Transcript.id)
            ).fetchall()
            count_transcripts += len(t_updated)

        session.commit()
        print(f"Backfill complete. Meetings updated: {count_meetings}, Transcripts updated: {count_transcripts}")


if __name__ == "__main__":
    backfill_org_ids()
