"""Wave 4 unit tests: Unified Plugin SDK (`core.nexus_framework.sdk`), Principal capability scopes,
zero plugin ORM imports, vendor-agnostic core, and HookManager + PipelineContext stage tracking.
"""

from __future__ import annotations

import ast
from pathlib import Path
import pytest

from core.hook_manager import HookManager
from core.nexus_framework import plugin_SDK as legacy_plugin_sdk
from core.nexus_framework import sdk as unified_sdk_pkg
from core.nexus_framework.sdk import (
    ACTIVE_PIPELINE_HOOK_CAPABILITIES,
    RETIRED_UNSUBSCRIBED_HOOK_STAGES,
    PipelineStage,
    build_plugin_principal,
    compute_plugin_crc32,
    pipeline_context_scope,
    sdk,
)
from core.nexus_framework.sdk import context as sdk_context
from core.nexus_framework.sdk import contracts as sdk_contracts
from core.nexus_framework.sdk import facades as sdk_facades
from core.plugins.sdk import (
    compute_plugin_crc32 as legacy_plugins_crc32,
    hookimpl as legacy_plugins_hookimpl,
    sdk as legacy_plugins_sdk_obj,
    verify_file_signature as legacy_plugins_verify_sig,
)
from core.security.rbac import Principal, principal_scope
from core.settings import config_manager
from database.config_database import close_config_database, get_config_database
from database.music_database import Artist, Base as MusicBase, LocalMedia, Track, close_database, get_database
from database.working_database import close_working_database, get_working_database

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def isolated_wave4_env(tmp_path, monkeypatch):
    """Isolated temporary config, working, and music databases so runtime DBs are never touched."""
    close_config_database()
    close_working_database()
    close_database()

    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    plugins_dir = tmp_path / "plugins"
    for d in (data_dir, config_dir, plugins_dir):
        d.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("ECHOSYNC_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ECHOSYNC_CONFIG_DIR", str(config_dir))

    config_uri = f"sqlite:///{(data_dir / 'config.db').as_posix()}"
    working_uri = f"sqlite:///{(data_dir / 'working.db').as_posix()}"
    music_uri = f"sqlite:///{(data_dir / 'music_library.db').as_posix()}"

    overrides = {
        "database.config_uri": config_uri,
        "database.working_uri": working_uri,
        "database.music_uri": music_uri,
    }
    original_get = config_manager.get

    def mock_get(key, default=None):
        if key in overrides:
            return overrides[key]
        return original_get(key, default)

    monkeypatch.setattr(config_manager, "get", mock_get)
    monkeypatch.setattr(config_manager, "get_plugins_dir", lambda: plugins_dir)
    monkeypatch.setattr(config_manager, "plugins_path", plugins_dir)

    config_db = get_config_database()
    working_db = get_working_database()
    music_db = get_database()
    MusicBase.metadata.create_all(music_db.engine)

    try:
        yield {
            "tmp_path": tmp_path,
            "config_db": config_db,
            "working_db": working_db,
            "music_db": music_db,
            "plugins_dir": plugins_dir,
        }
    finally:
        close_config_database()
        close_working_database()
        close_database()


def test_sdk_package_unification_and_backward_compatible_reexports():
    """Verify core.nexus_framework.sdk package structure and legacy module re-exports."""
    assert hasattr(sdk_facades, "sdk")
    assert hasattr(sdk_contracts, "PluginBase")
    assert hasattr(sdk_context, "PipelineContext")

    assert unified_sdk_pkg.sdk is legacy_plugin_sdk.sdk
    assert unified_sdk_pkg.sdk is legacy_plugins_sdk_obj
    assert unified_sdk_pkg.PluginBase is legacy_plugin_sdk.PluginBase
    assert unified_sdk_pkg.compute_plugin_crc32 is legacy_plugins_crc32
    assert unified_sdk_pkg.hookimpl is legacy_plugins_hookimpl
    assert unified_sdk_pkg.verify_file_signature is legacy_plugins_verify_sig

    assert sdk.library is not None
    assert sdk.working is not None
    assert sdk.accounts is not None
    assert sdk.config is not None
    assert sdk.db is not None


def test_principal_capability_scopes_and_plugin_secrets_denial(isolated_wave4_env):
    """Verify Principal contract:<entity>:<action> enforcement and explicit plugin secrets denial."""
    config_db = isolated_wave4_env["config_db"]
    plugin_crc = compute_plugin_crc32("EchoSync.test_provider")
    config_db.register_service(
        name="EchoSync.test_provider",
        service_type="provider",
        description="Test Provider",
        plugin_id=plugin_crc,
    )
    svc_id = config_db.get_service_id(plugin_crc)
    acc_id = config_db.ensure_account(service_id=svc_id, account_name="acct1", display_name="Account 1")
    config_db.save_account_token(acc_id, "secret_access", "secret_refresh", "Bearer", 9999999999, "read")

    # 1. Any Principal with principal_type == "plugin" is strictly denied contract:accounts:secrets
    plugin_principal = build_plugin_principal("EchoSync.test_provider", scopes=("*", "contract:accounts:secrets"))
    assert plugin_principal.principal_type == "plugin"
    assert plugin_principal.has_scope("contract:accounts:secrets") is False

    with pytest.raises(PermissionError, match="contract:accounts:secrets"):
        sdk.accounts.get_token(acc_id, principal=plugin_principal)

    with principal_scope(plugin_principal):
        with pytest.raises(PermissionError, match="contract:accounts:secrets"):
            sdk.accounts.get_token(acc_id)

    # 2. System/User principal WITH contract:accounts:secrets can read token
    system_principal = Principal(
        user_id="sys",
        username="system",
        principal_type="system",
        roles=("admin",),
        scopes=frozenset({"contract:accounts:secrets"}),
    )
    tok = sdk.accounts.get_token(acc_id, principal=system_principal)
    assert tok is not None
    assert tok["access_token"] == "secret_access"

    # 3. Facade methods enforce contract:<entity>:<read|edit|delete>[:own|:any]
    read_only_principal = Principal(
        user_id="u1",
        username="reader",
        principal_type="user",
        roles=("member",),
        scopes=frozenset({"contract:config:read:own", "contract:tracks:read", "contract:downloads:read"}),
    )
    assert sdk.config.get("nonexistent_key", "fallback", principal=read_only_principal) == "fallback"

    with pytest.raises(PermissionError, match="contract:config:edit:own"):
        sdk.config.set("some_key", "some_val", principal=read_only_principal)

    with pytest.raises(PermissionError, match="contract:accounts:edit:own"):
        sdk.accounts.save_token(acc_id, "a", "r", 123, principal=read_only_principal)

    with pytest.raises(PermissionError, match="contract:accounts:delete:own"):
        sdk.accounts.delete_account(acc_id, principal=read_only_principal)

    with pytest.raises(PermissionError, match="contract:downloads:edit"):
        sdk.working.transition_download_to_verifying(1, principal=read_only_principal)

    with pytest.raises(PermissionError, match="contract:tracks:delete"):
        sdk.library.cleanup_library_database(principal=read_only_principal)


def test_sdk_library_and_working_facades_roundtrip(isolated_wave4_env):
    """Verify sdk.library and sdk.working operations on isolated temporary databases."""
    music_db = isolated_wave4_env["music_db"]
    working_db = isolated_wave4_env["working_db"]
    tmp_path = isolated_wave4_env["tmp_path"]

    audio_path = tmp_path / "valid_song.flac"
    audio_path.write_bytes(b"fake flac content")
    ghost_path = tmp_path / "missing_ghost.flac"

    with music_db.session_scope() as session:
        artist = Artist(name="Test Artist", normalized_name="test artist")
        orphan_artist = Artist(name="Orphan Artist", normalized_name="orphan artist")
        session.add_all([artist, orphan_artist])
        session.flush()

        track1 = Track(
            title="Signed Song",
            normalized_title="signed song",
            artist_id=artist.id,
            sync_id="ss:track:meta:signed1",
            echosync_signature="blake3_sig_123",
            duration=210000,
        )
        track2 = Track(
            title="Ghost Song",
            normalized_title="ghost song",
            artist_id=artist.id,
            sync_id="ss:track:meta:ghost2",
        )
        session.add_all([track1, track2])
        session.flush()

        media1 = LocalMedia(
            media_id="med_valid_1",
            track_id=track1.id,
            file_path=audio_path.as_posix(),
            file_format="flac",
        )
        media2 = LocalMedia(
            media_id="med_ghost_2",
            track_id=track2.id,
            file_path=ghost_path.as_posix(),
            file_format="flac",
        )
        session.add_all([media1, media2])
        session.commit()
        t1_id = track1.id

    # sdk.library.signed_tracks_scope finds signed track
    with sdk.library.signed_tracks_scope() as (sess, signed_tracks):
        assert len(signed_tracks) == 1
        assert signed_tracks[0].id == t1_id
        assert sdk.db.get_object_session(signed_tracks[0]) is sess

    # sdk.library.cleanup_library_database evicts ghost media, orphaned track2, and orphan_artist
    stats = sdk.library.cleanup_library_database(
        db=music_db,
        sanctioned_prefixes=(tmp_path.as_posix(),),
        skip_rogue_sweep=False,
    )
    assert stats["missing_media"] == 1
    assert stats["deleted_tracks"] == 1
    assert stats["deleted_artists"] == 1

    # sdk.working download queue operations
    from core.database.models.working import DownloadQueue, DownloadStatus

    DownloadQueue.__table__.create(working_db.engine, checkfirst=True)
    with working_db.session_scope() as w_sess:
        item = DownloadQueue(
            id=77,
            active_candidate_id="peer_user|remote/folder/mysong.flac",
            plugin_id="EchoSync.slskd",
            status=DownloadStatus.DOWNLOADING.value,
            echo_sync_track={"title": "mysong.flac", "file_path": "mysong.flac"},
        )
        w_sess.add(item)
        w_sess.commit()

    resolved_id = sdk.working.resolve_active_download_task_id(filename="mysong.flac", username="peer_user")
    assert resolved_id == 77

    uname, transfer_id = sdk.working.get_download_candidate_identity(77)
    assert uname == "peer_user"
    assert transfer_id == "remote/folder/mysong.flac"

    assert sdk.working.transition_download_to_verifying(77, file_path=audio_path.as_posix()) is True
    with working_db.session_scope() as w_sess:
        reloaded = w_sess.get(DownloadQueue, 77)
        assert reloaded.status == DownloadStatus.VERIFYING.value
        assert reloaded.echo_sync_track["downloaded_file_path"] == audio_path.as_posix()


def test_plugins_have_zero_direct_database_or_sqlalchemy_imports():
    """Verify AST of the 5 Wave 4 plugin packages contains zero direct database.* or sqlalchemy imports."""
    target_plugin_dirs = [
        REPO_ROOT / "plugins" / "EchoSync" / "cjk_language_pack",
        REPO_ROOT / "plugins" / "EchoSync" / "local_metadata",
        REPO_ROOT / "plugins" / "EchoSync" / "local_server",
        REPO_ROOT / "plugins" / "EchoSync" / "slskd",
        REPO_ROOT / "plugins" / "EchoSync" / "spotify",
    ]
    forbidden_roots = {"database", "sqlalchemy"}
    forbidden_prefixes = ("core.database.models",)

    violations: list[str] = []
    for plugin_dir in target_plugin_dirs:
        assert plugin_dir.exists(), f"Missing expected plugin dir: {plugin_dir}"
        for py_file in sorted(plugin_dir.rglob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        if root in forbidden_roots or alias.name.startswith(forbidden_prefixes):
                            violations.append(f"{py_file.relative_to(REPO_ROOT)}:{node.lineno} import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    root = node.module.split(".")[0]
                    if root in forbidden_roots or node.module.startswith(forbidden_prefixes):
                        violations.append(f"{py_file.relative_to(REPO_ROOT)}:{node.lineno} from {node.module}")

    assert not violations, "Direct database/SQLAlchemy imports found in plugins:\n" + "\n".join(violations)


def test_core_matching_engine_and_nexus_framework_are_vendor_agnostic():
    """Verify zero vendor-specific names ('plex', 'jellyfin', 'spotify', 'slskd', 'acoustid') in core modules."""
    forbidden_vendors = ("plex", "jellyfin", "spotify", "slskd", "acoustid")
    target_files = [
        REPO_ROOT / "core" / "matching_engine" / "matching_engine.py",
        *sorted((REPO_ROOT / "core" / "nexus_framework").rglob("*.py")),
    ]

    found: list[str] = []
    for py_file in target_files:
        text_lower = py_file.read_text(encoding="utf-8").lower()
        for vendor in forbidden_vendors:
            if vendor in text_lower:
                found.append(f"{py_file.relative_to(REPO_ROOT)} contains '{vendor}'")

    assert not found, "Vendor-specific naming found in core:\n" + "\n".join(found)


def test_hook_manager_pipeline_context_stages_and_capability_gating():
    """Verify the 16 retired hooks track stages in PipelineContext and 7 active CJK filters enforce capabilities."""
    assert len(RETIRED_UNSUBSCRIBED_HOOK_STAGES) == 16
    expected_cjk_hooks = {
        "register_metadata_requirements": "pipeline:enrich",
        "post_metadata_enrichment": "pipeline:enrich",
        "pre_provider_search": "pipeline:intercept",
        "pre_normalize_text": "pipeline:intercept",
        "pre_normalize_title": "pipeline:intercept",
        "scoring_modifier": "pipeline:intercept",
        "search_expansion": "pipeline:intercept",
    }
    for hook_name, cap in expected_cjk_hooks.items():
        assert ACTIVE_PIPELINE_HOOK_CAPABILITIES.get(hook_name) == cap

    hm = HookManager()

    # 1. Capability gating on the 7 active CJK hooks
    unprivileged_plugin = build_plugin_principal("ThirdParty.no_caps", scopes=())
    with pytest.raises(PermissionError, match="pipeline:intercept"):
        hm.add_filter("pre_normalize_text", lambda s: s, principal=unprivileged_plugin)

    with pytest.raises(PermissionError, match="pipeline:enrich"):
        hm.add_filter("post_metadata_enrichment", lambda t: t, principal=unprivileged_plugin)

    intercept_plugin = build_plugin_principal("EchoSync.cjk_language_pack", scopes=("pipeline:intercept", "pipeline:enrich"))
    hm.add_filter("pre_normalize_text", lambda s: s.strip(), principal=intercept_plugin)
    hm.add_filter("post_metadata_enrichment", lambda t: t, principal=intercept_plugin)

    # Runtime execution under principal lacking capability raises PermissionError
    with principal_scope(unprivileged_plugin):
        with pytest.raises(PermissionError, match="pipeline:intercept"):
            hm.apply_filters("pre_normalize_text", "  hello  ")

    with principal_scope(intercept_plugin):
        assert hm.apply_filters("pre_normalize_text", "  hello  ") == "hello"

    # 2. Explicit PipelineContext stage tracking for retired unsubscribed hooks
    with pipeline_context_scope(pipeline_name="matching_pipeline", entity_type="track", entity_id=101) as ctx:
        with ctx.stage(PipelineStage.INGEST_PRE_TRACK, source="unit_test"):
            pass
        val = hm.apply_filters("ON_SCORING_WEIGHTS_CALCULATE", {"text_weight": 0.6})
        assert val == {"text_weight": 0.6}
        hm.trigger("ON_WEBHOOK_RECEIVED", plugin_id=123, slug="status", payload={})

        assert PipelineStage.INGEST_PRE_TRACK.value in ctx.stage_names
        assert PipelineStage.SCORING_WEIGHTS_CALCULATE.value in ctx.stage_names
        assert PipelineStage.WEBHOOK_RECEIVED.value in ctx.stage_names

        serialized = ctx.to_dict()
        assert serialized["pipeline_name"] == "matching_pipeline"
        assert serialized["entity_id"] == 101
        assert len(serialized["stages"]) == 3
