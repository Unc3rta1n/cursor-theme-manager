"""Standalone launchers retain the existing installation and cleanup boundary."""

import importlib.util
import os
import shutil
import sys
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cleanup_helper
import integration_manager
import secure_state
from test_isolation import IsolatedTestCase


class StandaloneIntegrationTests(IsolatedTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.iso.plugin_dir.rmdir()
        self.standalone = self.iso.root / "standalone-checkout"
        self.standalone.mkdir(parents=True)
        scripts = self.standalone / "scripts"
        scripts.mkdir()
        shutil.copyfile(ROOT / "scripts" / "cleanup_helper.py", scripts / "cleanup_helper.py")
        self.source = mock.patch.object(integration_manager, "SCRIPT_DIR", scripts)
        self.source.start()
        self.addCleanup(self.source.stop)
        self.mode = mock.patch.dict(os.environ, {"CTM_STANDALONE": "1"})
        self.mode.start()
        self.addCleanup(self.mode.stop)
        (self.standalone / "cursor-theme-manager").write_text("#!/bin/sh\nexit 0\n")
        (self.standalone / "cursor-theme-manager").chmod(0o755)
        self.assertEqual(integration_manager.get_plugin_installation_path(), str(self.standalone))
        identity = integration_manager.ensure_installation_identity()
        self.assertTrue(identity["ok"], identity)

    def test_discovers_standalone_installation(self) -> None:
        self.assertEqual(integration_manager.get_plugin_installation_path(), str(self.standalone))
        self.assertEqual(integration_manager.get_paths()["plugin_dir"], str(self.standalone))

    def test_launcher_and_removal_watcher_target_standalone(self) -> None:
        result = integration_manager.enable_integration()
        self.assertTrue(result["ok"], result)
        paths = integration_manager.get_paths()
        desktop = Path(paths["desktop"]).read_text()
        self.assertIn(str(self.standalone / "cursor-theme-manager"), desktop)
        self.assertNotIn("Exec=omarchy-shell", desktop)
        self.assertTrue(integration_manager.is_file_owned_by_us(paths["desktop"]))
        watcher = Path(paths["path_unit"]).read_text()
        self.assertIn(str(self.standalone), watcher)
        self.assertNotIn("PathChanged=%h/.config/omarchy/plugins", watcher)
        for line in watcher.splitlines():
            if line.startswith("PathChanged="):
                self.assertTrue(line.startswith("PathChanged=/"), line)

    def test_copied_cleanup_remembers_installation_after_directory_removal(self) -> None:
        result = integration_manager.enable_integration()
        self.assertTrue(result["ok"], result)
        cleanup = Path(integration_manager.get_paths()["cleanup"])
        # The installed helper intentionally has no extension.
        loader = SourceFileLoader("standalone_cleanup", str(cleanup))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        shutil.rmtree(self.standalone)
        self.assertEqual(module.get_paths()["plugin_dir"], str(self.standalone))

    def test_running_checkout_wins_over_other_installed_copies(self) -> None:
        other = self.iso.xdg_config / "quickshell" / "cursor-theme-manager"
        other.mkdir(parents=True)
        self.iso.plugin_dir.mkdir()
        self.assertEqual(integration_manager.get_plugin_installation_path(), str(self.standalone))

    def test_standalone_reconciles_orphaned_state_without_legacy_plugin_directory(self) -> None:
        fingerprint = integration_manager.get_plugin_installation_fingerprint()
        state = secure_state.read_state()
        state["integrationPluginFingerprint"] = "a" * 64
        self.assertTrue(secure_state.write_state(state))
        result = cleanup_helper.reconcile_orphaned_state(
            fingerprint, installation_path=str(self.standalone),
        )
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["reconciled"], result)
        self.assertFalse((self.iso.state_dir / "state.json").exists())

    def test_discovery_reports_actual_size_without_persisting_a_selection(self) -> None:
        loader = SourceFileLoader("standalone_cursorctl", str(ROOT / "scripts" / "cursorctl"))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)

        def query(args: list[str], **kwargs: object) -> SimpleNamespace:
            value = "28" if args[-1] == "cursor-size" else "'gruvbox-light'"
            return SimpleNamespace(ok=True, stdout=value)

        with mock.patch.dict(os.environ, {"XDG_DATA_DIRS": str(self.iso.sys_data)}), \
                mock.patch.object(module, "run_bounded", side_effect=query), \
                mock.patch.object(module, "emit_bounded_json") as emit:
            module.run_discover()
        result = emit.call_args.args[0]
        self.assertEqual(result["currentSize"], 28)
        self.assertEqual(result["currentXcursor"], "gruvbox-light")
        self.assertFalse((self.iso.state_dir / "state.json").exists())

    def test_first_size_change_keeps_theme_for_next_login(self) -> None:
        loader = SourceFileLoader("standalone_size", str(ROOT / "scripts" / "cursorctl"))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        baseline = {"captured": True, "gtkThemeSet": True, "gtkTheme": "gruvbox-light", "gtkSize": 28}
        with mock.patch.object(secure_state, "capture_original_cursor", return_value=baseline), \
                mock.patch.object(module, "run_bounded", return_value=SimpleNamespace(ok=True, stdout="")), \
                mock.patch.object(module, "sync_x11_and_gtk_cursor"):
            module.run_persist_size("gruvbox-light", "gruvbox-light", 32)
        state = secure_state.read_state()
        self.assertEqual(state["size"], 32)
        self.assertEqual(state["theme"]["hyprcursor"], "gruvbox-light")
        self.assertEqual(state["theme"]["xcursor"], "gruvbox-light")
        self.assertEqual(state["preCtmCursor"]["gtkSize"], 28)

    def test_failed_watcher_rollback_is_reported_without_leaving_the_launcher(self) -> None:
        def command(args: list[str], **kwargs: object) -> SimpleNamespace:
            failed = "enable" in args or "disable" in args
            return SimpleNamespace(ok=not failed, stdout="", stderr="simulated failure" if failed else "",
                                   error="", exit_code=1 if failed else 0, timed_out=False, limit_exceeded=False)

        with mock.patch.object(integration_manager, "run_bounded", side_effect=command):
            result = integration_manager.enable_integration()
        self.assertFalse(result["ok"])
        self.assertIn("rollback incomplete", result["error"])
        self.assertFalse(Path(integration_manager.get_paths()["desktop"]).exists())


if __name__ == "__main__":
    unittest.main()
