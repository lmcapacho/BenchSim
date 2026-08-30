"""Tests for the shared release update flow."""

import unittest
from unittest.mock import Mock, patch

from benchsim.update_controller import UpdateController
from benchsim.updater import select_release_asset


class _MessageBox:
    """Small Qt-free message box double for update controller tests."""

    class StandardButton:
        Yes = object()

    question = Mock(return_value=StandardButton.Yes)
    information = Mock()
    warning = Mock()


class UpdateTests(unittest.TestCase):
    """Verify platform package selection and installer launch behavior."""

    def test_prefers_windows_installer_asset(self):
        assets = [
            {"name": "BenchSim-v0.1.2-linux-x86_64.tar.gz", "url": "linux"},
            {"name": "BenchSim-v0.1.2-windows-x64-setup.exe", "url": "setup"},
            {"name": "BenchSim-v0.1.2-windows-x64-portable.zip", "url": "portable"},
        ]
        with patch("benchsim.updater.sys.platform", "win32"):
            self.assertEqual(select_release_asset(assets)["url"], "setup")

    def test_windows_update_downloads_and_closes_after_installer_launch(self):
        settings = Mock()
        settings.get_config.return_value = {"update_include_prerelease": False}
        controller = UpdateController(
            settings=settings,
            translate=lambda key, _lang, **kwargs: key,
            language_getter=lambda: "en",
            message_box=_MessageBox,
        )
        parent = Mock()
        result = {
            "ok": True,
            "update_available": True,
            "current_version": "0.1.1",
            "latest_version": "0.1.2",
            "selected_asset": {"name": "BenchSim-v0.1.2-windows-x64-setup.exe", "url": "asset"},
            "release_url": "https://example.invalid/release",
        }

        with patch("benchsim.update_controller.check_updates_remote", return_value=result), \
             patch("benchsim.update_controller.download_asset", return_value="C:/updates/BenchSim-setup.exe") as download, \
             patch("benchsim.update_controller.launch_installer", return_value=True) as launch, \
             patch("benchsim.update_controller.sys.platform", "win32"):
            controller.check_for_updates(parent)

        download.assert_called_once_with(result["selected_asset"])
        launch.assert_called_once_with("C:/updates/BenchSim-setup.exe")
        parent.close.assert_called_once()
