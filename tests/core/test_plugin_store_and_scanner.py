"""Tests for PluginStore lowercase path canonicalization, rollback on reload ERROR, and PluginSecurityScanner."""

import ast
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.nexus_framework.plugin_loader import PluginSecurityScanner
from core.nexus_framework.plugin_store import PluginSecurityError, PluginStore
from core.task_manager import PluginLifecycleState, plugin_state_manager


def _make_plugin_zip(manifest: dict, code: str = "def register(): pass\n") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("__init__.py", code)
    return buf.getvalue()


def _scan_source(source: str) -> list[tuple[int, str]]:
    tree = ast.parse(source)
    scanner = PluginSecurityScanner(privileged=False)
    scanner.visit(tree)
    return scanner.violations


class TestPluginStoreCanonicalPathsAndRollback:
    def test_a_installs_titlecase_plugin_into_lowercase_beta_path(self, tmp_path, monkeypatch):
        """Test A: plugin_store installs EchoSync.Spotify into lowercase EchoSync/spotify/beta."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)

        store = PluginStore()
        store.plugins_dir = plugins_dir

        manifest = {
            "id": "EchoSync.Spotify",
            "name": "Spotify",
            "author": "EchoSync",
            "version": "2.4.2",
            "beta_version": "2.4.3-beta.1",
            "type": "metadata",
        }
        zip_bytes = _make_plugin_zip(manifest)

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.content = zip_bytes

        mock_db = MagicMock()
        mock_db.database_path = str(tmp_path / "config.db")

        with (
            patch("core.nexus_framework.plugin_store.RequestManager") as mock_req_cls,
            patch("database.config_database.get_config_database", return_value=mock_db),
            patch("core.nexus_framework.plugin_store.db_write_lease"),
            patch("core.nexus_framework.plugin_loader._sync_ui_components_to_db"),
            patch("core.settings.config_manager.set"),
        ):
            mock_req_cls.return_value.get.return_value = fake_resp
            ok = store.download_plugin(
                {
                    "id": "EchoSync.Spotify",
                    "name": "Spotify",
                    "beta_url": "https://raw.githubusercontent.com/bheem1224/EchoSync/main/plugins/EchoSync/spotify/beta.zip",
                    "beta_version": "2.4.3-beta.1",
                },
                channel="beta",
                force_consent=True,
                is_update=False,
            )

        assert ok is True
        expected_beta = plugins_dir / "EchoSync" / "spotify" / "beta"
        assert expected_beta.exists()
        assert (expected_beta / "manifest.json").is_file()
        # Verify register_service received lowercase path segment
        mock_db.register_service.assert_called_once()
        reg_kwargs = mock_db.register_service.call_args.kwargs
        assert "spotify" in Path(reg_kwargs["absolute_install_path"]).parts

    def test_c_failed_reload_error_state_triggers_rollback_and_raises(self, tmp_path, caplog):
        """Test C: Failed security scan during reload_plugin rolls back beta_backup and raises PluginSecurityError."""
        plugins_dir = tmp_path / "plugins"
        target_dir = plugins_dir / "EchoSync" / "spotify" / "beta"
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "manifest.json").write_text(
            json.dumps({"id": "EchoSync.Spotify", "name": "Spotify", "author": "EchoSync", "version": "2.4.2"}),
            encoding="utf-8",
        )
        (target_dir / "__init__.py").write_text("# healthy v1\n", encoding="utf-8")

        store = PluginStore()
        store.plugins_dir = plugins_dir

        new_manifest = {
            "id": "EchoSync.Spotify",
            "name": "Spotify",
            "author": "EchoSync",
            "version": "2.4.3-beta.2",
            "type": "metadata",
        }
        zip_bytes = _make_plugin_zip(new_manifest, code="import os\n")

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.content = zip_bytes

        mock_db = MagicMock()
        mock_db.database_path = str(tmp_path / "config.db")
        mock_db.get_service_id.return_value = None

        reload_calls = []

        def fake_reload(plugin_id_int, absolute_install_path=None):
            reload_calls.append((plugin_id_int, absolute_install_path))
            if len(reload_calls) == 1:
                plugin_state_manager.set_state(
                    "spotify",
                    PluginLifecycleState.ERROR,
                    "Plugin failed security scanner on reload.",
                )
                return False
            plugin_state_manager.set_state("spotify", PluginLifecycleState.READY, "Restored")
            return True

        with (
            patch("core.nexus_framework.plugin_store.RequestManager") as mock_req_cls,
            patch("database.config_database.get_config_database", return_value=mock_db),
            patch("database.working_database.get_working_database"),
            patch("core.nexus_framework.plugin_store.db_write_lease"),
            patch("core.settings.config_manager.set"),
            patch("core.nexus_framework.plugin_loader.PluginLoader") as mock_loader_cls,
        ):
            mock_req_cls.return_value.get.return_value = fake_resp
            mock_loader_cls.return_value.reload_plugin.side_effect = fake_reload

            with pytest.raises(PluginSecurityError, match="security scanner"):
                store.download_plugin(
                    {
                        "id": "EchoSync.Spotify",
                        "name": "Spotify",
                        "beta_url": "https://raw.githubusercontent.com/bheem1224/EchoSync/main/plugins/EchoSync/spotify/beta.zip",
                        "beta_version": "2.4.3-beta.2",
                    },
                    channel="beta",
                    force_consent=True,
                    is_update=True,
                    target_plugin_id=12345,
                )

        # Verify rollback restored healthy v1 code and re-reloaded it
        assert (target_dir / "__init__.py").read_text(encoding="utf-8") == "# healthy v1\n"
        assert len(reload_calls) == 2
        assert "Live-swap successful" not in caplog.text


class TestPluginSecurityScannerRefinement:
    def test_b_allows_safe_getattr_and_blocks_dangerous_introspection(self):
        """Test B: safe getattr(track, 'title', None) allowed; dunder/dynamic/os/config.db blocked."""
        assert _scan_source('val = getattr(track, "title", None)') == []
        assert _scan_source('val = getattr(track, "duration")') == []

        assert _scan_source('g = getattr(obj, "__globals__")')
        assert _scan_source('d = getattr(obj, "__dict__")')
        assert _scan_source('s = getattr(obj, "__subclasses__")')
        assert _scan_source('x = getattr(obj, dynamic_name)')
        assert _scan_source('x = getattr(os, "system")')
        assert _scan_source("import os")
        assert _scan_source('path = "sqlite:///config.db"')

    def test_d_all_15_bundled_plugins_pass_scanner_and_have_valid_manifests(self):
        """Test D: All 15 bundled plugins pass PluginSecurityScanner with zero violations and declare two-tier scopes."""
        bundled_root = Path(__file__).resolve().parents[2] / "plugins" / "EchoSync"
        plugin_dirs = sorted(
            p for p in bundled_root.iterdir() if p.is_dir() and p.name != "__pycache__"
        )
        assert len(plugin_dirs) == 15

        for pdir in plugin_dirs:
            manifest_path = pdir / "manifest.json"
            assert manifest_path.is_file(), f"Missing manifest.json in {pdir.name}"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            caps = manifest.get("capabilities")
            assert isinstance(caps, list) and len(caps) > 0, f"{pdir.name} missing capabilities list"
            assert "contract:accounts:secrets" not in caps, f"{pdir.name} must never declare contract:accounts:secrets"
            assert all(c.startswith(("contract:", "service:", "pipeline:")) for c in caps), (
                f"{pdir.name} has non-two-tier capability: {caps}"
            )
            if pdir.name == "local_server":
                assert "privileged" not in manifest and "privileged_mode" not in manifest

            for py_file in sorted(pdir.rglob("*.py")):
                tree = ast.parse(py_file.read_text(encoding="utf-8", errors="ignore"), filename=str(py_file))
                scanner = PluginSecurityScanner(privileged=False)
                scanner.visit(tree)
                assert scanner.violations == [], (
                    f"{pdir.name}/{py_file.name} failed security scan: {scanner.violations}"
                )
