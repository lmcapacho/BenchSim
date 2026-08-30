"""Controller for startup and manual update checks."""

import sys
import webbrowser

from PyQt6.QtWidgets import QMessageBox

from .updater import (
    check_for_updates as check_updates_remote,
    download_asset,
    get_current_version,
    launch_installer,
)


class UpdateController:
    """Handle update checks and user prompts."""

    def __init__(self, *, settings, translate, language_getter):
        self.settings = settings
        self._tr = translate
        self.language_getter = language_getter

    def maybe_check_updates_on_startup(self, parent_widget):
        """Check for updates on startup when enabled in settings."""
        cfg = self.settings.get_config()
        if not cfg.get("update_auto_check", True):
            return
        self.check_for_updates(parent_widget, silent_errors=True)

    def check_for_updates(
        self,
        parent_widget,
        *,
        silent_errors=False,
        include_prerelease=None,
        current_version=None,
        on_installer_launched=None,
    ):
        """Check releases and use one download/install flow from every entry point."""
        cfg = self.settings.get_config()
        lang = self.language_getter()
        if include_prerelease is None:
            include_prerelease = cfg.get("update_include_prerelease", False)
        result = check_updates_remote(
            current_version=current_version or get_current_version(),
            include_prerelease=include_prerelease,
        )

        if not result.get("ok"):
            if not silent_errors:
                QMessageBox.warning(
                    parent_widget,
                    self._tr("popup_warning_title", lang),
                    self._tr("update_check_failed", lang, error=result.get("error", "unknown")),
                )
            return

        if not result.get("update_available"):
            if not silent_errors:
                QMessageBox.information(
                    parent_widget,
                    self._tr("popup_info_title", lang),
                    self._tr("update_not_available", lang, version=result.get("current_version", "?")),
                )
            return

        answer = QMessageBox.question(
            parent_widget,
            self._tr("update_available_title", lang),
            self._tr(
                "update_available_body",
                lang,
                current=result.get("current_version", "?"),
                latest=result.get("latest_version", "?"),
            ),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        asset = result.get("selected_asset")
        if not asset:
            QMessageBox.information(
                parent_widget,
                self._tr("popup_info_title", lang),
                self._tr("update_asset_not_found", lang),
            )
            webbrowser.open(result.get("release_url", ""))
            return

        try:
            package_path = download_asset(asset)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            QMessageBox.warning(
                parent_widget,
                self._tr("popup_warning_title", lang),
                self._tr("update_download_failed", lang, error=str(exc)),
            )
            webbrowser.open(result.get("release_url", ""))
            return

        QMessageBox.information(
            parent_widget,
            self._tr("popup_info_title", lang),
            self._tr("update_download_done", lang, path=package_path),
        )

        try:
            launched = launch_installer(package_path)
        except Exception:  # pylint: disable=broad-exception-caught
            launched = False

        if launched and sys.platform.startswith("win") and package_path.lower().endswith(".exe"):
            QMessageBox.information(
                parent_widget,
                self._tr("popup_info_title", lang),
                self._tr("update_launching_installer", lang),
            )
            if on_installer_launched:
                on_installer_launched()
            else:
                parent_widget.close()
            return

        QMessageBox.information(
            parent_widget,
            self._tr("popup_info_title", lang),
            self._tr("update_manual_install_hint", lang),
        )
