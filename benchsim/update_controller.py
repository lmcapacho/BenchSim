"""Controller for startup/manual update checks."""

import webbrowser

from PyQt6.QtWidgets import QMessageBox

from .updater import check_for_updates as check_updates_remote, get_current_version


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

    def check_for_updates(self, parent_widget, silent_errors=False):
        """Check GitHub releases and offer opening the release page."""
        cfg = self.settings.get_config()
        lang = self.language_getter()
        include_prerelease = cfg.get("update_include_prerelease", False)
        result = check_updates_remote(
            current_version=get_current_version(),
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
        if answer == QMessageBox.StandardButton.Yes:
            webbrowser.open(result.get("release_url", ""))
