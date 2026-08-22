"""backfill_nanoid_sync_ids

Revision ID: f1e2d3c4b5a6
Revises: e11aada610d5
Create Date: 2026-08-22 00:00:00.000000

"""
import string
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1e2d3c4b5a6'
down_revision: Union[str, None] = 'e11aada610d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def generate_nanoid(size: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(size))


def upgrade() -> None:
    conn = op.get_bind()
    tracks = conn.execute(
        sa.text("SELECT id, sync_id FROM tracks WHERE sync_id LIKE 'ss:%'")
    ).fetchall()

    old_to_new = {}
    for track_id, old_sync_id in tracks:
        new_sync_id = generate_nanoid(8)
        conn.execute(
            sa.text("UPDATE tracks SET sync_id = :new_id WHERE id = :tid"),
            {"new_id": new_sync_id, "tid": track_id}
        )
        old_to_new[old_sync_id] = new_sync_id

    if hasattr(conn, "commit"):
        try:
            conn.commit()
        except Exception:
            pass

    # Cross-database update: working.db
    if old_to_new:
        try:
            from database.working_database import get_working_database
            working_db = get_working_database()
            with working_db.engine.begin() as wconn:
                for old_sync_id, new_sync_id in old_to_new.items():
                    base_old = old_sync_id.split("?")[0]
                    wconn.execute(
                        sa.text("UPDATE user_ratings SET sync_id = :new_id WHERE sync_id = :old_id OR sync_id = :base_old"),
                        {"new_id": new_sync_id, "old_id": old_sync_id, "base_old": base_old}
                    )
                    wconn.execute(
                        sa.text("UPDATE user_track_states SET sync_id = :new_id WHERE sync_id = :old_id OR sync_id = :base_old"),
                        {"new_id": new_sync_id, "old_id": old_sync_id, "base_old": base_old}
                    )
                    wconn.execute(
                        sa.text("UPDATE download_queue SET sync_id = :new_id WHERE sync_id = :old_id OR sync_id = :base_old"),
                        {"new_id": new_sync_id, "old_id": old_sync_id, "base_old": base_old}
                    )
        except Exception:
            pass


def downgrade() -> None:
    pass
