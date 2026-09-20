"""
Test auto-migrations linearity, single-head invariant, and execution safety.
Verifies:
1. Music migrations have strictly one head (no MultipleHeads).
2. All music migration scripts form a linear revision sequence.
3. run_auto_migrations() completes cleanly without crashing.
"""

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from core.db.migrations import run_auto_migrations
from database.music_database import get_database
from database.working_database import get_working_database


@pytest.fixture(autouse=True)
def cleanup_orphaned_alembic_tables():
    """Teardown/setup hook that explicitly drops orphaned _alembic_tmp_external_identifiers tables."""
    for db_getter in (get_database, get_working_database):
        try:
            db = db_getter()
            with db.engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS _alembic_tmp_external_identifiers;"))
                conn.commit()
        except Exception:
            pass

    yield

    for db_getter in (get_database, get_working_database):
        try:
            db = db_getter()
            with db.engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS _alembic_tmp_external_identifiers;"))
                conn.commit()
        except Exception:
            pass


def test_music_migrations_single_head():
    """Verify that database/migrations/music reports exactly one head revision."""
    music_ini = Path(__file__).resolve().parents[2] / "database" / "migrations" / "music" / "alembic.ini"
    assert music_ini.exists(), "database/migrations/music/alembic.ini must exist"

    cfg = Config(str(music_ini))
    cfg.set_main_option("script_location", str(music_ini.parent))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()

    assert len(heads) == 1, f"Expected exactly 1 head revision, got {heads}"
    assert heads[0] == "f3a4b5c6d7e8", f"Expected head 'f3a4b5c6d7e8', got {heads[0]}"


def test_music_migrations_strict_linearity():
    """Verify that there is a strict linear revision sequence from baseline to head."""
    repo_root = Path(__file__).resolve().parents[2]
    music_ini = repo_root / "database" / "migrations" / "music" / "alembic.ini"

    cfg = Config(str(music_ini))
    cfg.set_main_option("script_location", str(music_ini.parent))
    script = ScriptDirectory.from_config(cfg)

    head_rev = script.get_revision("f3a4b5c6d7e8")
    assert head_rev is not None

    # Walk backwards from head to baseline
    visited = []
    curr = head_rev
    while curr is not None:
        visited.append(curr.revision)
        if curr.down_revision is None:
            break
        # Assert down_revision is a single string (not a tuple of multiple heads)
        assert isinstance(curr.down_revision, str), (
            f"Revision {curr.revision} has non-linear down_revision: {curr.down_revision}"
        )
        curr = script.get_revision(curr.down_revision)

    assert "d4a8e2b9c1f0" in visited, "d4a8e2b9c1f0 must be in the linear history"
    assert "a1b2c3d4e5f6" in visited, "a1b2c3d4e5f6 must be in the linear history"
    assert "e2f3a4b5c6d7" in visited, "e2f3a4b5c6d7 must be in the linear history"
    assert "7b7461716632" in visited, "7b7461716632 (baseline) must be at the root of the history"


def test_run_auto_migrations_succeeds():
    """Verify that run_auto_migrations() succeeds without throwing MultipleHeads."""
    # This must execute without raising any exception
    run_auto_migrations()
