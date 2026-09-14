"""
Anti-regression integration test suite for PR branch feature/cjk-nexus-permissions-refactor.

Validates:
1. Real zip download/extraction, unseeded permission registration, and clean sys.modules hot-swap under Python 3.12.
2. Cross-database SQLite WAL concurrency under heavy load (MusicDatabase 3,000+ row inserts concurrent with ConfigDatabase reader/writer threads).
3. Auto-seeding of SAFE_BASE_SCOPES for unseeded/omitted permissions and strict revocation on explicit opt-outs.
4. Senior Architect Code Review blocker defects: dynamic plugin path registration via config_manager, elimination of author security bypass, preservation of beta_opt_in channel preferences across reload, and re-entrant db_write_lease.
"""

import json
import os
import sys
import threading
import time
import zipfile
from unittest.mock import patch

import pytest

from core.nexus_framework.plugin_loader import PluginLoader, PluginRegistry
from core.nexus_framework.plugin_SDK import (
    check_plugin_permission,
    sdk,
)
from core.plugins.sdk import compute_plugin_crc32
from core.settings import config_manager
from database.config_database import (
    ConfigDatabase,
    close_config_database,
)
from database.music_database import (
    Artist,
    MusicDatabase,
    Track,
    close_database,
    init_music_db,
)


@pytest.fixture
def regression_env(tmp_path, monkeypatch):
    """Sets up an isolated filesystem and database environment for integration regression testing."""
    close_config_database()
    close_database()

    config_db_path = tmp_path / "config.db"
    music_db_path = tmp_path / "music.db"
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(tmp_path / "data/plugins/data", exist_ok=True)

    config_uri = f"sqlite:///{config_db_path.as_posix()}"
    music_uri = f"sqlite:///{music_db_path.as_posix()}"

    orig_get = config_manager.get

    def mock_get(key, default=None):
        if key == "database.config_uri":
            return config_uri
        if key == "database.music_uri":
            return music_uri
        return orig_get(key, default)

    monkeypatch.setattr(config_manager, "get", mock_get)
    monkeypatch.setattr(config_manager, "get_plugins_dir", lambda: plugins_dir)
    monkeypatch.setattr(config_manager, "plugins_path", plugins_dir)

    config_db = ConfigDatabase(db_path=str(config_db_path))
    music_db = MusicDatabase(database_path=str(music_db_path))
    init_music_db(music_db.engine)

    try:
        yield {
            "tmp_path": tmp_path,
            "plugins_dir": plugins_dir,
            "config_db": config_db,
            "music_db": music_db,
            "config_db_path": config_db_path,
            "music_db_path": music_db_path,
            "monkeypatch": monkeypatch,
        }
    finally:
        close_config_database()
        close_database()


# =========================================================================
# 1. Real Zip Package Live-Swap Lifecycle
# =========================================================================


def test_real_zip_live_swap_lifecycle(regression_env):
    """Downloads/unzips a mock plugin package on a temporary disk path, registers it with
    unseeded permissions, triggers hot-swap, and verifies sys.modules clean reload.
    """
    tmp_path = regression_env["tmp_path"]
    plugins_dir = regression_env["plugins_dir"]
    config_db = regression_env["config_db"]

    author = "test_live_vendor"
    plugin_name = "test_live_swap"
    full_id = f"{author}.{plugin_name}"
    plugin_crc32 = compute_plugin_crc32(full_id)

    dest_dir = plugins_dir / author / plugin_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    # 1. Construct v1 artifact zip
    v1_manifest = {
        "id": full_id,
        "author": author,
        "name": plugin_name,
        "version": "1.0.0",
        "description": "Live Swap Test Plugin v1",
        "permissions": {},
    }
    v1_code = f"""
from core.nexus_framework.plugin_SDK import PluginBase

class TestLiveSwapPlugin(PluginBase):
    name = "{full_id}"
    version = "1.0.0"
    TAG = "VERSION_1_RUNNING"
"""
    v1_zip_path = tmp_path / "v1.zip"
    with zipfile.ZipFile(v1_zip_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(v1_manifest, indent=2))
        zf.writestr("__init__.py", v1_code)

    # Extract v1 to disk
    with zipfile.ZipFile(v1_zip_path, "r") as zf:
        zf.extractall(dest_dir)

    # Register plugins_dir in plugins.__path__ so dynamic subpackages resolve under Python 3.12
    import plugins

    if hasattr(plugins, "__path__") and str(plugins_dir) not in plugins.__path__:
        plugins.__path__.append(str(plugins_dir))

    # Register in config.db with unseeded permissions ("{}")
    config_db.register_service(
        name=full_id,
        service_type="provider",
        description="Live Swap Test Plugin",
        absolute_install_path=str(dest_dir.resolve()),
        plugin_id=plugin_crc32,
        version="1.0.0",
        permissions="{}",
    )

    # Load initial v1 module
    loader = PluginLoader(tmp_path)
    loaded_v1 = loader._load_plugin_package(
        plugin_id=plugin_crc32,
        is_beta=False,
        absolute_install_path=str(dest_dir.resolve()),
    )
    assert loaded_v1 is True

    # Verify v1 is in sys.modules and registry
    expected_mod = f"plugins.{author}.{plugin_name}"
    assert expected_mod in sys.modules
    v1_cls = PluginRegistry.get_plugin_class(full_id)
    assert v1_cls is not None
    assert getattr(v1_cls, "TAG", "") == "VERSION_1_RUNNING"

    # 2. Construct v2 artifact zip (updated code)
    v2_manifest = {
        "id": full_id,
        "author": author,
        "name": plugin_name,
        "version": "2.0.0",
        "description": "Live Swap Test Plugin v2",
        "permissions": {},
    }
    v2_code = f"""
from core.nexus_framework.plugin_SDK import PluginBase

class TestLiveSwapPlugin(PluginBase):
    name = "{full_id}"
    version = "2.0.0"
    TAG = "VERSION_2_HOT_SWAPPED"
"""
    v2_zip_path = tmp_path / "v2.zip"
    with zipfile.ZipFile(v2_zip_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(v2_manifest, indent=2))
        zf.writestr("__init__.py", v2_code)

    # Simulate artifact delivery & swap on disk
    with zipfile.ZipFile(v2_zip_path, "r") as zf:
        zf.extractall(dest_dir)

    # Update version in config.db
    with config_db._get_connection() as conn:
        conn.execute("UPDATE services SET version = '2.0.0' WHERE plugin_id = ?", (plugin_crc32,))
        conn.commit()

    # 3. Trigger hot-swap reload
    loader.reload_plugin(plugin_crc32)

    # 4. Verify sys.modules clean reload
    assert expected_mod in sys.modules
    v2_cls = PluginRegistry.get_plugin_class(full_id)
    assert v2_cls is not None
    assert getattr(v2_cls, "TAG", "") == "VERSION_2_HOT_SWAPPED"
    assert v2_cls.version == "2.0.0"


# =========================================================================
# 2. Cross-Database SQLite WAL Bulk Sync Concurrency
# =========================================================================


def test_sqlite_wal_bulk_sync_concurrency(regression_env):
    """Runs simulated concurrent queries and mutations across MusicDatabase and ConfigDatabase
    under real SQLite WAL mode with 3,000+ batch inserts to assert zero unhandled
    sqlite3.OperationalError: disk I/O error or database is locked.
    """
    config_db = regression_env["config_db"]
    music_db = regression_env["music_db"]

    # Pre-create artist for track inserts
    with music_db.session_scope() as session:
        artist = Artist(name="Bulk Benchmark Artist")
        session.add(artist)
        session.flush()
        artist_id = artist.id

    NUM_ITEMS = 3000
    BATCH_SIZE = 100
    stop_event = threading.Event()
    errors: list[Exception] = []

    def bulk_music_worker():
        """Inserts 3,000+ tracks into MusicDatabase in batches."""
        try:
            for batch_start in range(0, NUM_ITEMS, BATCH_SIZE):
                if stop_event.is_set():
                    break
                with music_db.session_scope() as session:
                    for i in range(batch_start, batch_start + BATCH_SIZE):
                        t = Track(
                            title=f"Benchmark Track {i}",
                            artist_id=artist_id,
                            duration=180000 + i,
                        )
                        session.add(t)
        except Exception as exc:
            errors.append(exc)
        finally:
            stop_event.set()

    def config_writer_worker():
        """Repeatedly updates service config and system settings in ConfigDatabase."""
        counter = 0
        while not stop_event.is_set():
            try:
                counter += 1
                config_db.set_service_config(
                    service_id=99999,
                    key=f"sync_key_{counter % 10}",
                    value=f"value_{counter}",
                )
                config_db.set_system_setting(
                    key="system.sync_heartbeat",
                    value={"counter": counter, "timestamp": time.time()},
                )
            except Exception as exc:
                errors.append(exc)
                break

    def config_reader_worker():
        """Repeatedly reads service config and system settings from ConfigDatabase."""
        while not stop_event.is_set():
            try:
                _ = config_db.get_service_config(service_id=99999, key="sync_key_1")
                _ = config_db.get_all_system_settings()
                _ = config_db.get_service_credentials("system")
            except Exception as exc:
                errors.append(exc)
                break

    # Spawn concurrent threads across both databases
    threads = [
        threading.Thread(target=bulk_music_worker, name="MusicBulkWorker"),
        threading.Thread(target=config_writer_worker, name="ConfigWriterWorker"),
        threading.Thread(target=config_reader_worker, name="ConfigReaderWorker1"),
        threading.Thread(target=config_reader_worker, name="ConfigReaderWorker2"),
    ]

    for t in threads:
        t.start()

    # Join bulk worker first, which drives stop_event
    threads[0].join(timeout=60.0)
    stop_event.set()

    for t in threads[1:]:
        t.join(timeout=10.0)

    # Assert zero unhandled SQLite operational errors
    assert len(errors) == 0, f"Encountered unhandled SQLite errors during cross-DB WAL concurrency: {errors}"

    # Verify data integrity
    with music_db.session_scope() as session:
        count = session.query(Track).filter(Track.artist_id == artist_id).count()
        assert count == NUM_ITEMS

    heartbeat = config_db.get_system_setting("system.sync_heartbeat")
    assert heartbeat is not None
    assert "counter" in heartbeat


# =========================================================================
# 3. Permission Auto-Seeding vs. Explicit Opt-Out
# =========================================================================


def test_explicit_opt_out_vs_omitted_permissions(regression_env):
    """Validates that omitted/unseeded scopes yield True for SAFE_BASE_SCOPES,
    while explicit False in manifest or DB strictly revokes read permissions.
    Also validates that write/mutation scopes strictly require explicit grants.
    """
    db = regression_env["config_db"]
    plugins_dir = regression_env["plugins_dir"]

    # 1. Unseeded / Omitted permissions: Must auto-grant SAFE_BASE_SCOPES
    unseeded_id = "EchoSync.unseeded_test"
    crc_unseeded = compute_plugin_crc32(unseeded_id)
    db.register_service(
        name=unseeded_id,
        service_type="provider",
        description="Unseeded Plugin",
        plugin_id=crc_unseeded,
        version="1.0.0",
        permissions="{}",  # Empty permissions in database
    )

    # Omitted base scopes return True
    assert check_plugin_permission(unseeded_id, "database.read_library") is True
    assert check_plugin_permission(unseeded_id, "metadata.read") is True
    assert check_plugin_permission(unseeded_id, "read_library") is True
    assert check_plugin_permission(unseeded_id, "metadata") is True

    # Omitted mutation scopes return False (least privilege)
    assert check_plugin_permission(unseeded_id, "database.mutate_working") is False
    assert check_plugin_permission(unseeded_id, "database.mutate_aliases") is False
    assert check_plugin_permission(unseeded_id, "privileged_mode") is False

    # 2. Explicit False in Database: Must strictly revoke
    denied_db_id = "EchoSync.denied_db_test"
    crc_denied_db = compute_plugin_crc32(denied_db_id)
    db.register_service(
        name=denied_db_id,
        service_type="provider",
        description="Explicit Denied in DB",
        plugin_id=crc_denied_db,
        version="1.0.0",
        permissions=json.dumps({"database": {"read_library": False}}),
    )
    assert check_plugin_permission(denied_db_id, "database.read_library") is False

    # 3. Explicit False in Manifest on Disk: Must strictly revoke
    denied_manifest_id = "EchoSync.denied_manifest_test"
    crc_denied_manifest = compute_plugin_crc32(denied_manifest_id)
    manifest_folder = plugins_dir / "EchoSync" / "denied_manifest_test"
    manifest_folder.mkdir(parents=True, exist_ok=True)
    manifest_payload = {
        "id": denied_manifest_id,
        "author": "EchoSync",
        "name": "denied_manifest_test",
        "version": "1.0.0",
        "permissions": {
            "read_library": False,
        },
    }
    (manifest_folder / "manifest.json").write_text(json.dumps(manifest_payload), encoding="utf-8")

    db.register_service(
        name=denied_manifest_id,
        service_type="provider",
        description="Explicit Denied in Manifest",
        plugin_id=crc_denied_manifest,
        version="1.0.0",
        permissions="{}",
    )
    assert check_plugin_permission(denied_manifest_id, "database.read_library") is False

    # 4. Database Connection Write Access Enforcement
    # When write_access=True, requires database.mutate_working or privileged_mode
    with patch.object(sdk, "_get_plugin_id", return_value=unseeded_id):
        # Read-only succeeds for unseeded
        read_engine = sdk.get_database_connection(write_access=False)
        assert read_engine is not None

        # Write access fails with PermissionError
        with pytest.raises(PermissionError) as exc_info:
            sdk.get_database_connection(write_access=True)
        assert "mutate_working" in str(exc_info.value)

    # Grant mutate_working in DB and test write access succeeds
    with db._get_connection() as conn:
        conn.execute(
            "UPDATE services SET permissions = ? WHERE plugin_id = ?",
            (json.dumps(["database.read_library", "database.mutate_working"]), crc_unseeded),
        )
        conn.commit()

    with patch.object(sdk, "_get_plugin_id", return_value=unseeded_id):
        write_engine = sdk.get_database_connection(write_access=True)
        assert write_engine is not None


# =========================================================================
# 4. Senior Architect Review Regression Suite (Blocker Defect Mitigations)
# =========================================================================


def test_dynamic_plugin_path_registration(regression_env):
    """Verifies that PluginLoader dynamically queries config_manager.get_plugins_dir()
    and prepends the resolved directory to sys.modules['plugins'].__path__, eliminating
    hardcoded container paths like /data/plugins.
    """
    tmp_path = regression_env["tmp_path"]
    plugins_dir = regression_env["plugins_dir"]
    config_db = regression_env["config_db"]

    author = "dynamic_vendor"
    plugin_name = "dynamic_path_test"
    full_id = f"{author}.{plugin_name}"
    plugin_crc32 = compute_plugin_crc32(full_id)

    dest_dir = plugins_dir / author / plugin_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "id": full_id,
        "author": author,
        "name": plugin_name,
        "version": "1.0.0",
        "description": "Dynamic Path Test Plugin",
        "permissions": {},
    }
    code = f"""
from core.nexus_framework.plugin_SDK import PluginBase

class DynamicPathPlugin(PluginBase):
    name = "{full_id}"
    version = "1.0.0"
"""
    (dest_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (dest_dir / "__init__.py").write_text(code, encoding="utf-8")

    config_db.register_service(
        name=full_id,
        service_type="provider",
        description="Dynamic Path Test",
        absolute_install_path=str(dest_dir.resolve()),
        plugin_id=plugin_crc32,
        version="1.0.0",
    )

    import plugins

    # Ensure plugins.__path__ does not have plugins_dir before loading
    plugins_dir_resolved = str(plugins_dir.resolve())
    if hasattr(plugins, "__path__") and plugins_dir_resolved in plugins.__path__:
        plugins.__path__.remove(plugins_dir_resolved)

    loader = PluginLoader(tmp_path)
    loaded = loader._load_plugin_package(
        plugin_id=plugin_crc32,
        is_beta=False,
        absolute_install_path=str(dest_dir.resolve()),
    )
    assert loaded is True

    # Assert dynamic path was registered into sys.modules['plugins'].__path__
    assert "plugins" in sys.modules
    assert plugins_dir_resolved in sys.modules["plugins"].__path__
    expected_mod = f"plugins.{author}.{plugin_name}"
    assert expected_mod in sys.modules


def test_author_security_bypass_elimination(regression_env):
    """Validates that plugins with author 'EchoSync' do NOT bypass the security scanner.
    Any forbidden AST operations (such as bare open() or direct database imports)
    must fail validation and be rejected from loading.
    """
    tmp_path = regression_env["tmp_path"]
    plugins_dir = regression_env["plugins_dir"]

    author = "EchoSync"
    plugin_name = "malicious_spoof"
    full_id = f"{author}.{plugin_name}"

    dest_dir = plugins_dir / author / plugin_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "id": full_id,
        "author": "EchoSync",  # Spoof official author
        "name": plugin_name,
        "version": "1.0.0",
        "description": "Spoofed Official Plugin with Forbidden IO",
        "permissions": {},
    }
    # Contains forbidden bare open() call
    forbidden_code = """
from core.nexus_framework.plugin_SDK import PluginBase

class SpoofedPlugin(PluginBase):
    name = "EchoSync.malicious_spoof"

    def execute(self):
        f = open("/etc/passwd", "r")
        return f.read()
"""
    (dest_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (dest_dir / "__init__.py").write_text(forbidden_code, encoding="utf-8")

    loader = PluginLoader(tmp_path)

    # Security scanner must reject this package despite author == 'EchoSync'
    is_clean = loader._security_scan_package(dest_dir, full_id, privileged=False)
    assert is_clean is False, "Security scan should have failed for bare open() call!"

    # In load_plugins(), the plugin must NOT be loaded
    # Seed service in DB as active
    config_db = regression_env["config_db"]
    crc = compute_plugin_crc32(full_id)
    config_db.register_service(
        name=full_id,
        service_type="provider",
        description="Spoofed Plugin",
        absolute_install_path=str(dest_dir.resolve()),
        plugin_id=crc,
        version="1.0.0",
    )

    # Calling load_all() should not load this rejected plugin into PluginRegistry
    loader.load_all()
    assert PluginRegistry.get_plugin_class(full_id) is None


def test_register_service_preserves_beta_opt_in(regression_env):
    """Verifies that ConfigDatabase.register_service preserves the user's beta_opt_in
    preference when updated with beta_opt_in=None (default on reload/update),
    while correctly applying explicit updates (0 or 1) and defaulting new rows to 0.
    """
    config_db = regression_env["config_db"]

    test_plugin_id = 88776655
    service_name = "EchoSync.channel_preservation_test"

    # 1. First registration with explicit beta_opt_in = 1
    config_db.register_service(
        name=service_name,
        service_type="provider",
        description="Channel Test Initial",
        plugin_id=test_plugin_id,
        version="1.0.0",
        beta_opt_in=1,
    )

    with config_db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT beta_opt_in FROM services WHERE plugin_id = ?", (test_plugin_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 1

    # 2. Subsequent registration/reload with beta_opt_in=None (default)
    # Must PRESERVE beta_opt_in = 1 and NOT overwrite with default 0
    config_db.register_service(
        name=service_name,
        service_type="provider",
        description="Channel Test Reloaded",
        plugin_id=test_plugin_id,
        version="1.0.1",
        beta_opt_in=None,
    )

    with config_db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT beta_opt_in, version FROM services WHERE plugin_id = ?", (test_plugin_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 1, "beta_opt_in was overwritten with default 0 during reload!"
        assert row[1] == "1.0.1"

    # 3. Explicit update to beta_opt_in = 0
    config_db.register_service(
        name=service_name,
        service_type="provider",
        description="Channel Test Downgrade",
        plugin_id=test_plugin_id,
        version="1.0.2",
        beta_opt_in=0,
    )

    with config_db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT beta_opt_in FROM services WHERE plugin_id = ?", (test_plugin_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 0, "Explicit beta_opt_in=0 was not applied!"

    # 4. Brand new service without beta_opt_in specified defaults to 0
    new_plugin_id = 99887766
    config_db.register_service(
        name="EchoSync.brand_new_service",
        service_type="provider",
        description="Brand New Service",
        plugin_id=new_plugin_id,
        version="1.0.0",
    )

    with config_db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT beta_opt_in FROM services WHERE plugin_id = ?", (new_plugin_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 0, "New service without beta_opt_in should default to 0!"


def test_reentrant_db_write_lease_in_service_registration(regression_env):
    """Verifies that register_service correctly operates within db_write_lease,
    supports re-entrant acquisitions, and enforces unsigned 32-bit plugin_id.
    """
    from core.task_manager import db_write_lease

    config_db = regression_env["config_db"]
    test_plugin_id = 0xFFFFFFFF  # Max unsigned 32-bit int

    # Call register_service within an active outer write lease (re-entrancy check)
    with db_write_lease(task_name="outer_lease"):
        config_db.register_service(
            name="EchoSync.lease_test",
            service_type="provider",
            description="Lease Reentrancy Test",
            plugin_id=test_plugin_id,
            version="1.0.0",
        )

    with config_db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT plugin_id FROM services WHERE name = 'EchoSync.lease_test'")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == test_plugin_id
