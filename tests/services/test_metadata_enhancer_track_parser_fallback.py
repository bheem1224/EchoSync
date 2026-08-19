import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from database.working_database import ReviewTask, get_working_database
from services.metadata_enhancer import RetroactiveEnhancer
from core.matching_engine.track_parser import TrackParser

def test_track_parser_fallback_on_unidentified_file(tmp_path):
    """Test that when native tags and remote identification return None, TrackParser populates artist & title."""
    file_path = tmp_path / "Kendrick Lamar - Alright.wav"
    file_path.write_bytes(b"RIFF....WAVEfmt ")

    enhancer = RetroactiveEnhancer()

    # Call create_or_update_review_task with empty tags/metadata
    enhancer.create_or_update_review_task(
        file_path=file_path,
        decision="No confident match found",
        match_data=None,
        status="pending",
        confidence_score=0.0
    )

    db = get_working_database()
    with db.session_scope() as session:
        task = session.query(ReviewTask).filter(ReviewTask.file_path == str(file_path)).first()
        assert task is not None
        assert task.status == "pending"
        assert task.track_data is not None
        assert task.track_data.get("artist_name") == "Kendrick Lamar"
        assert task.track_data.get("title") == "Alright"
