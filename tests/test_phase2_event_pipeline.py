from __future__ import annotations

import inspect
import time
from importlib import import_module
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.working_database import UserRating, WorkingBase


def _import_or_skip(module_name: str):
    try:
        return import_module(module_name)
    except Exception as exc:  # pragma: no cover - skip path depends on branch state
        pytest.skip(f"{module_name} unavailable in this branch: {exc}")


def _new_event_bus_instance():
    """Return a fresh event bus instance from core.event_bus (preferred) or fallback module."""
    bus_module = None
    try:
        bus_module = import_module("core.event_bus")
    except Exception:
        try:
            bus_module = import_module("web.utils.event_bus")
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"No event bus module available: {exc}")

    if hasattr(bus_module, "EventBus"):
        return bus_module.EventBus()

    if hasattr(bus_module, "event_bus"):
        return bus_module.event_bus

    pytest.skip("Event bus module does not expose EventBus or event_bus")


def _subscribe_lightweight(bus: Any, event_name: str, handler: Callable[[dict], None]) -> None:
    if not hasattr(bus, "subscribe"):
        pytest.skip("Event bus does not expose subscribe()")

    subscribe = getattr(bus, "subscribe")
    try:
        subscribe(event_name, handler)
        return
    except TypeError:
        pass

    try:
        subscribe(handler)
        return
    except TypeError:
        pass

    raise AssertionError("Unable to subscribe with expected lightweight API")


def _publish_lightweight(bus: Any, payload: dict) -> None:
    if not hasattr(bus, "publish"):
        raise AssertionError("Event bus does not expose publish()")

    publish = getattr(bus, "publish")

    # Phase-2 target API: publish(payload_dict)
    try:
        publish(payload)
        return
    except TypeError:
        pass

    # Common transitional API: publish(event_name, payload_dict)
    try:
        publish(payload.get("event"), payload)
        return
    except TypeError:
        pass

    # Legacy API in older branches: publish(channel, event_type, data)
    publish("phase2-test", payload.get("event"), payload)


def _invoke_parser(parser: Any, payload: dict) -> None:
    for method_name in ("parse_and_publish", "parse", "handle", "process"):
        if hasattr(parser, method_name):
            getattr(parser, method_name)(payload)
            return
    raise AssertionError("Parser has no supported parse entrypoint")


def _extract_payload_from_publish_call(mock_publish: MagicMock) -> dict:
    assert mock_publish.call_count >= 1, "event_bus.publish was never called"
    args, kwargs = mock_publish.call_args

    for value in list(args) + list(kwargs.values()):
        if isinstance(value, dict) and "event" in value and "sync_id" in value and "data" in value:
            return value

    raise AssertionError("Could not find lightweight event payload in publish() arguments")


def test_event_bus_payload_schema():
    bus = _new_event_bus_instance()
    received: list[dict] = []

    payload = {
        "event": "TRACK_RATED",
        "sync_id": "ss:track:mbid:123",
        "data": {"rating": 8.0, "user_id": 1},
    }

    def _handler(event_payload: dict) -> None:
        received.append(event_payload)

    _subscribe_lightweight(bus, "TRACK_RATED", _handler)
    _publish_lightweight(bus, payload)

    assert received, "Subscriber did not receive any event payload"
    assert received[0]["event"] == "TRACK_RATED"
    assert received[0]["sync_id"] == "ss:track:mbid:123"
    assert received[0]["data"]["rating"] == 8.0
    assert received[0]["data"]["user_id"] == 1


def test_sync_lightweight_batch_diffing(monkeypatch: pytest.MonkeyPatch):
    sync_module = _import_or_skip("services.sync_service")

    if not hasattr(sync_module, "PlaylistSyncService"):
        pytest.skip("PlaylistSyncService not found")

    service_cls = sync_module.PlaylistSyncService
    if not hasattr(service_cls, "sync_lightweight_batch"):
        pytest.skip("sync_lightweight_batch() not present in this branch")

    # Build a minimally configured service instance and inject mocked collaborators.
    service = service_cls.__new__(service_cls)

    input_sync_ids = [
        "ss:track:mbid:one",
        "ss:track:mbid:two",
        "ss:track:mbid:three",
    ]
    existing = set(input_sync_ids[:2])
    missing = [input_sync_ids[2]]

    mock_db = MagicMock()
    mock_db.get_existing_sync_ids.return_value = existing
    mock_db.bulk_existing_sync_ids.return_value = existing
    mock_db.fetch_existing_sync_ids.return_value = existing

    mock_provider = MagicMock()
    mock_provider.fetch_tracks_by_sync_ids.return_value = [{"sync_id": missing[0]}]
    mock_provider.fetch_by_sync_ids.return_value = [{"sync_id": missing[0]}]
    mock_provider.fetch_tracks.return_value = [{"sync_id": missing[0]}]

    # Inject common attribute names used by different implementations.
    for attr_name in ("music_db", "library_db", "db", "music_database"):
        setattr(service, attr_name, mock_db)
    for attr_name in ("provider", "provider_client", "active_provider", "source_provider"):
        setattr(service, attr_name, mock_provider)

    # Execute method under test.
    result = service.sync_lightweight_batch(input_sync_ids)
    if inspect.isawaitable(result):
        import asyncio

        result = asyncio.run(result)

    fetch_calls = (
        mock_provider.fetch_tracks_by_sync_ids.call_count
        + mock_provider.fetch_by_sync_ids.call_count
        + mock_provider.fetch_tracks.call_count
    )
    assert fetch_calls == 1, "Provider fetch should run exactly once for missing sync_ids"

    called_args = []
    for method in (
        mock_provider.fetch_tracks_by_sync_ids,
        mock_provider.fetch_by_sync_ids,
        mock_provider.fetch_tracks,
    ):
        if method.call_count:
            args, kwargs = method.call_args
            called_args.extend(args)
            called_args.extend(kwargs.values())

    called_arg_text = " ".join(str(x) for x in called_args)
    assert missing[0] in called_arg_text


def test_plex_webhook_publishes_event():
    parser_module = _import_or_skip("core.webhook_parsers")

    if not hasattr(parser_module, "PlexWebhookParser"):
        pytest.skip("PlexWebhookParser not found")

    parser_cls = parser_module.PlexWebhookParser
    event_bus = MagicMock()

    try:
        parser = parser_cls(event_bus=event_bus)
    except TypeError:
        parser = parser_cls()
        if hasattr(parser, "event_bus"):
            parser.event_bus = event_bus
        else:
            pytest.skip("PlexWebhookParser does not accept or expose event_bus")

    payload = {
        "event": "media.rate",
        "Metadata": {
            "title": "Song Title",
            "grandparentTitle": "Artist Name",
            "guid": "mbid://123",
            "userRating": 8.0,
        },
        "Account": {"id": 1},
    }

    _invoke_parser(parser, payload)

    published = _extract_payload_from_publish_call(event_bus.publish)
    assert published["event"] == "TRACK_RATED"
    assert published["sync_id"].startswith("ss:track:mbid:")
    # userRating=8.0 is Plex wire format (4 displayed stars); parser halves it to 4.0 display stars
    assert published["data"]["rating"] == 4.0
    assert published["data"]["user_id"] == 1


def test_state_listener_writes_to_db():
    listener_module = _import_or_skip("services.state_listener")
    if not hasattr(listener_module, "StateListenerService"):
        pytest.skip("StateListenerService not found")

    bus = _new_event_bus_instance()

    # In-memory working database schema used by this test only.
    engine = create_engine("sqlite:///:memory:", future=True)
    WorkingBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    listener_cls = listener_module.StateListenerService
    init_sig = inspect.signature(listener_cls)
    kwargs = {}

    if "event_bus" in init_sig.parameters:
        kwargs["event_bus"] = bus
    elif "bus" in init_sig.parameters:
        kwargs["bus"] = bus

    if "session_factory" in init_sig.parameters:
        kwargs["session_factory"] = Session
    elif "session_maker" in init_sig.parameters:
        kwargs["session_maker"] = Session
    elif "engine" in init_sig.parameters:
        kwargs["engine"] = engine

    listener = listener_cls(**kwargs)

    # Some implementations subscribe on explicit startup.
    for hook_name in ("start", "subscribe", "register_handlers"):
        if hasattr(listener, hook_name):
            getattr(listener, hook_name)()

    payload = {
        "event": "TRACK_RATED",
        "sync_id": "ss:track:mbid:123",
        "data": {"rating": 8.0, "user_id": 1},
    }
    _publish_lightweight(bus, payload)

    # Give async/event-loop listeners a short processing window.
    time.sleep(0.05)

    with Session() as session:
        row = session.query(UserRating).filter_by(sync_id="ss:track:mbid:123", user_id=1).one_or_none()
        assert row is not None
        assert row.rating == 8.0

    engine.dispose()
    args, kwargs = mock_publish.call_args

    for value in list(args) + list(kwargs.values()):
        if isinstance(value, dict) and "event" in value and "sync_id" in value and "data" in value:
            return value

    raise AssertionError("Could not find lightweight event payload in publish() arguments")


def test_event_bus_payload_schema():
    bus = _new_event_bus_instance()
    received: list[dict] = []

    payload = {
        "event": "TRACK_RATED",
        "sync_id": "ss:track:mbid:123",
        "data": {"rating": 8.0, "user_id": 1},
    }

    def _handler(event_payload: dict) -> None:
        received.append(event_payload)

    _subscribe_lightweight(bus, "TRACK_RATED", _handler)
    _publish_lightweight(bus, payload)

    assert received, "Subscriber did not receive any event payload"
    assert received[0]["event"] == "TRACK_RATED"
    assert received[0]["sync_id"] == "ss:track:mbid:123"
    assert received[0]["data"]["rating"] == 8.0
    assert received[0]["data"]["user_id"] == 1


def test_sync_lightweight_batch_diffing(monkeypatch: pytest.MonkeyPatch):
    sync_module = _import_or_skip("services.sync_service")

    if not hasattr(sync_module, "PlaylistSyncService"):
        pytest.skip("PlaylistSyncService not found")

    service_cls = sync_module.PlaylistSyncService
    if not hasattr(service_cls, "sync_lightweight_batch"):
        pytest.skip("sync_lightweight_batch() not present in this branch")

    # Build a minimally configured service instance and inject mocked collaborators.
    service = service_cls.__new__(service_cls)

    input_sync_ids = [
        "ss:track:mbid:one",
        "ss:track:mbid:two",
        "ss:track:mbid:three",
    ]
    existing = set(input_sync_ids[:2])
    missing = [input_sync_ids[2]]

    mock_db = MagicMock()
    mock_db.get_existing_sync_ids.return_value = existing
    mock_db.bulk_existing_sync_ids.return_value = existing
    mock_db.fetch_existing_sync_ids.return_value = existing

    mock_provider = MagicMock()
    mock_provider.fetch_tracks_by_sync_ids.return_value = [{"sync_id": missing[0]}]
    mock_provider.fetch_by_sync_ids.return_value = [{"sync_id": missing[0]}]
    mock_provider.fetch_tracks.return_value = [{"sync_id": missing[0]}]

    # Inject common attribute names used by different implementations.
    for attr_name in ("music_db", "library_db", "db", "music_database"):
        setattr(service, attr_name, mock_db)
    for attr_name in ("provider", "provider_client", "active_provider", "source_provider"):
        setattr(service, attr_name, mock_provider)

    # Execute method under test.
    result = service.sync_lightweight_batch(input_sync_ids)
    if inspect.isawaitable(result):
        import asyncio

        result = asyncio.run(result)

    fetch_calls = (
        mock_provider.fetch_tracks_by_sync_ids.call_count
        + mock_provider.fetch_by_sync_ids.call_count
        + mock_provider.fetch_tracks.call_count
    )
    assert fetch_calls == 1, "Provider fetch should run exactly once for missing sync_ids"

    called_args = []
    for method in (
        mock_provider.fetch_tracks_by_sync_ids,
        mock_provider.fetch_by_sync_ids,
        mock_provider.fetch_tracks,
    ):
        if method.call_count:
            args, kwargs = method.call_args
            called_args.extend(args)
            called_args.extend(kwargs.values())

    called_arg_text = " ".join(str(x) for x in called_args)
    assert missing[0] in called_arg_text


def test_plex_webhook_publishes_event():
    parser_module = _import_or_skip("core.webhook_parsers")

    if not hasattr(parser_module, "PlexWebhookParser"):
        pytest.skip("PlexWebhookParser not found")

    parser_cls = parser_module.PlexWebhookParser
    event_bus = MagicMock()

    try:
        parser = parser_cls(event_bus=event_bus)
    except TypeError:
        parser = parser_cls()
        if hasattr(parser, "event_bus"):
            parser.event_bus = event_bus
        else:
            pytest.skip("PlexWebhookParser does not accept or expose event_bus")

    payload = {
        "event": "media.rate",
        "Metadata": {
            "title": "Song Title",
            "grandparentTitle": "Artist Name",
            "guid": "mbid://123",
            "userRating": 8.0,
        },
        "Account": {"id": 1},
    }

    _invoke_parser(parser, payload)

    published = _extract_payload_from_publish_call(event_bus.publish)
    assert published["event"] == "TRACK_RATED"
    assert published["sync_id"].startswith("ss:track:mbid:")
    assert published["data"]["rating"] == 4.0  # wire 8.0 ÷ 2 = 4.0 display stars
    assert published["data"]["user_id"] == 1


def test_state_listener_writes_to_db():
    listener_module = _import_or_skip("services.state_listener")
    if not hasattr(listener_module, "StateListenerService"):
        pytest.skip("StateListenerService not found")

    bus = _new_event_bus_instance()

    # In-memory working database schema used by this test only.
    engine = create_engine("sqlite:///:memory:", future=True)
    WorkingBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    listener_cls = listener_module.StateListenerService
    init_sig = inspect.signature(listener_cls)
    kwargs = {}

    if "event_bus" in init_sig.parameters:
        kwargs["event_bus"] = bus
    elif "bus" in init_sig.parameters:
        kwargs["bus"] = bus

    if "session_factory" in init_sig.parameters:
        kwargs["session_factory"] = Session
    elif "session_maker" in init_sig.parameters:
        kwargs["session_maker"] = Session
    elif "engine" in init_sig.parameters:
        kwargs["engine"] = engine

    listener = listener_cls(**kwargs)

    # Some implementations subscribe on explicit startup.
    for hook_name in ("start", "subscribe", "register_handlers"):
        if hasattr(listener, hook_name):
            getattr(listener, hook_name)()

    payload = {
        "event": "TRACK_RATED",
        "sync_id": "ss:track:mbid:123",
        "data": {"rating": 8.0, "user_id": 1},
    }
    _publish_lightweight(bus, payload)

    # Give async/event-loop listeners a short processing window.
    time.sleep(0.05)

    with Session() as session:
        row = session.query(UserRating).filter_by(sync_id="ss:track:mbid:123", user_id=1).one_or_none()
        assert row is not None
        assert row.rating == 8.0

    engine.dispose()