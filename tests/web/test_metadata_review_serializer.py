from database.working_database import ReviewTask
from web.routes.metadata_review import _serialize_task


def test_serialize_task_reflects_track_data_in_proposed_fields():
    """Ensure _serialize_task reflects track_data['artist_name'] and track_data['title'] in proposed_artist and proposed_title."""
    task = ReviewTask(
        id=42,
        file_path="/music/J. Cole - No Role Modelz.wav",
        status="pending",
        track_data={
            "artist_name": "J. Cole",
            "title": "No Role Modelz",
            "album_title": "2014 Forest Hills Drive",
            "display_title": "No Role Modelz",
        },
        confidence_score=0.0,
    )

    serialized = _serialize_task(task)
    assert serialized["id"] == 42
    assert serialized["proposed_artist"] == "J. Cole"
    assert serialized["proposed_title"] == "No Role Modelz"
    assert serialized["detected_metadata"]["artist"] == "J. Cole"
    assert serialized["detected_metadata"]["title"] == "No Role Modelz"


def test_serialize_task_includes_edition():
    """Ensure _serialize_task includes edition in detected_metadata and proposed_metadata."""
    task = ReviewTask(
        id=99,
        file_path="/music/ZAYN - Dusk Till Dawn (Radio Edit).flac",
        status="pending",
        track_data={
            "artist_name": "ZAYN",
            "title": "Dusk Till Dawn",
            "edition": "Radio Edit",
            "album_title": "Dusk Till Dawn",
        },
        confidence_score=0.9,
    )

    serialized = _serialize_task(task)
    assert serialized["detected_metadata"]["edition"] == "Radio Edit"
    assert serialized["proposed_metadata"]["edition"] == "Radio Edit"
