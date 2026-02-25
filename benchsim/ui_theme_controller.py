"""Controller for theme application and toolbar icon styling."""

import sys
from pathlib import Path

from PyQt6.QtGui import QColor, QIcon, QPainter
from PyQt6.QtWidgets import QStyle


def _get_tool_icon(widget, theme_name, fallback_icon):
    """Return icon and whether fallback icon was used."""
    icon = QIcon.fromTheme(theme_name)
    used_fallback = False
    if icon.isNull():
        icon = widget.style().standardIcon(fallback_icon)
        used_fallback = True
    return icon, used_fallback


class UIThemeController:
    """Apply app/editor theme and theme-aware toolbar icons."""

    def __init__(
        self,
        *,
        widget,
        base_dir,
        load_stylesheet,
        editor,
        external_change_bar,
        folder_button,
        reload_button,
        validate_tool_button,
        config_button,
    ):
        self.widget = widget
        self.base_dir = base_dir
        self.load_stylesheet = load_stylesheet
        self.editor = editor
        self.external_change_bar = external_change_bar
        self.folder_button = folder_button
        self.reload_button = reload_button
        self.validate_tool_button = validate_tool_button
        self.config_button = config_button

    def apply_theme(self, theme):
        """Apply UI and editor theme from external files."""
        resolved_theme = theme or "dark"
        theme_file = Path(self.base_dir) / "themes" / f"{resolved_theme}.qss"
        if not theme_file.is_file():
            theme_file = Path(self.base_dir) / "themes" / "dark.qss"
            resolved_theme = "dark"

        self.widget.setStyleSheet(self.load_stylesheet(theme_file))
        self._apply_external_change_bar_style(resolved_theme)
        self._apply_toolbar_icons(resolved_theme)
        self.editor.apply_theme(resolved_theme)
        return resolved_theme

    def _apply_external_change_bar_style(self, theme):
        """Apply theme-aware style for external-change banner."""
        if theme == "dark":
            bg = "#2A2414"
            border = "#6E5A24"
            text = "#F1E7CC"
            btn_bg = "#3A321D"
            btn_hover = "#4A4023"
            btn_border = "#6E5A24"
        else:
            bg = "#FFF6DD"
            border = "#D8BE7A"
            text = "#4A3A13"
            btn_bg = "#F8ECD0"
            btn_hover = "#F2E2BA"
            btn_border = "#D1B16B"
        self.external_change_bar.setStyleSheet(
            f"#externalChangeBar {{ background-color: {bg}; border: 1px solid {border}; border-radius: 2px; }}"
            f"#externalChangeBar QLabel {{ color: {text}; border: none; }}"
            f"#externalChangeBar QPushButton {{ background-color: {btn_bg}; border: 1px solid {btn_border}; padding: 3px 8px; }}"
            f"#externalChangeBar QPushButton:hover {{ background-color: {btn_hover}; }}"
        )

    def _apply_toolbar_icons(self, theme):
        """Apply system icons and tweak contrast where needed."""
        tint_color = QColor("#E4E4E4")
        on_windows_dark = sys.platform.startswith("win") and theme == "dark"

        buttons = [
            (self.folder_button, "folder-open", QStyle.StandardPixmap.SP_DirOpenIcon),
            (self.reload_button, "view-refresh", QStyle.StandardPixmap.SP_BrowserReload),
            (self.validate_tool_button, "dialog-ok-apply", QStyle.StandardPixmap.SP_DialogYesButton),
        ]
        for button, name, standard in buttons:
            icon, _fallback = _get_tool_icon(self.widget, name, standard)
            if on_windows_dark and not icon.isNull():
                icon = self._tint_icon(icon, tint_color)
            button.setIcon(icon)

        icon, fallback = _get_tool_icon(self.widget, "settings", QStyle.StandardPixmap.SP_FileDialogDetailedView)
        if fallback:
            alt = QIcon.fromTheme("preferences-system")
            if not alt.isNull():
                icon = alt
        if on_windows_dark and not icon.isNull():
            icon = self._tint_icon(icon, tint_color)
        self.config_button.setIcon(icon)

    @staticmethod
    def _tint_icon(icon, color):
        """Tint icon for dark backgrounds when fallback icon is too dark."""
        tinted = QIcon()
        for size in (16, 20, 24, 32):
            src = icon.pixmap(size, size)
            if src.isNull():
                continue
            dst = src.copy()
            painter = QPainter(dst)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(dst.rect(), color)
            painter.end()
            tinted.addPixmap(dst)
        return tinted if not tinted.isNull() else icon
