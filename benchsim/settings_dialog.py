"""Configuration dialog for tool paths, language, and update settings."""
import os
import webbrowser

# pylint: disable=no-name-in-module
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from .i18n import LANG_OPTIONS, normalize_lang, tr
from .settings_manager import SettingsManager
from .updater import check_for_updates, get_current_version

APP_NAME = "BenchSim"


class ConfigDialog(QDialog):
    """Dialog window for configuring tool paths and language."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = SettingsManager(APP_NAME)
        cfg = self.settings.get_config()
        self.language = normalize_lang(cfg.get("language", "en"))
        self.theme = cfg.get("theme", "dark")

        self.setGeometry(200, 200, 560, 300)
        self.setWindowTitle(tr("config_title", self.language))

        layout = QVBoxLayout()

        iverilog_label = QLabel(tr("config_iverilog", self.language))
        iverilog_layout = QHBoxLayout()
        self.iverilog_entry = QLineEdit()
        self.iverilog_button = QPushButton()
        self.iverilog_button.setObjectName("browseButton")
        self.iverilog_button.setIcon(self._browse_icon())
        self.iverilog_button.setIconSize(QSize(14, 14))
        self.iverilog_button.setFixedWidth(30)
        self.iverilog_button.clicked.connect(lambda: self.select_executable("iverilog"))
        iverilog_layout.addWidget(self.iverilog_entry)
        iverilog_layout.addWidget(self.iverilog_button)
        layout.addWidget(iverilog_label)
        layout.addLayout(iverilog_layout)

        gtkwave_label = QLabel(tr("config_gtkwave", self.language))
        gtkwave_layout = QHBoxLayout()
        self.gtkwave_entry = QLineEdit()
        self.gtkwave_button = QPushButton()
        self.gtkwave_button.setObjectName("browseButton")
        self.gtkwave_button.setIcon(self._browse_icon())
        self.gtkwave_button.setIconSize(QSize(14, 14))
        self.gtkwave_button.setFixedWidth(30)
        self.gtkwave_button.clicked.connect(lambda: self.select_executable("gtkwave"))
        gtkwave_layout.addWidget(self.gtkwave_entry)
        gtkwave_layout.addWidget(self.gtkwave_button)
        layout.addWidget(gtkwave_label)
        layout.addLayout(gtkwave_layout)

        language_label = QLabel(tr("config_language", self.language))
        self.language_combo = QComboBox()
        for code, label in LANG_OPTIONS.items():
            self.language_combo.addItem(label, code)
        self._set_language_combo(self.language)
        self.language_combo.currentIndexChanged.connect(self._refresh_theme_labels)
        layout.addWidget(language_label)
        layout.addWidget(self.language_combo)

        theme_label = QLabel(tr("config_theme", self.language))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("", "dark")
        self.theme_combo.addItem("", "light")
        self._set_theme_combo(self.theme)
        self._refresh_theme_labels()
        layout.addWidget(theme_label)
        layout.addWidget(self.theme_combo)

        self.update_auto_check = QCheckBox(tr("config_update_auto", self.language))
        self.update_auto_check.setChecked(cfg.get("update_auto_check", True))
        layout.addWidget(self.update_auto_check)

        self.update_include_prerelease = QCheckBox(tr("config_update_prerelease", self.language))
        self.update_include_prerelease.setChecked(cfg.get("update_include_prerelease", False))
        layout.addWidget(self.update_include_prerelease)

        self.check_updates_button = QPushButton(tr("config_check_updates_now", self.language))
        self.check_updates_button.clicked.connect(self.check_updates_now)
        layout.addWidget(self.check_updates_button)

        layout.addSpacing(15)
        self.save_button = QPushButton(tr("config_save", self.language))
        self.save_button.clicked.connect(self.save_config)
        layout.addWidget(self.save_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
        self.load_config()

    def _set_language_combo(self, lang):
        for idx in range(self.language_combo.count()):
            if self.language_combo.itemData(idx) == lang:
                self.language_combo.setCurrentIndex(idx)
                return

    def _set_theme_combo(self, theme):
        for idx in range(self.theme_combo.count()):
            if self.theme_combo.itemData(idx) == theme:
                self.theme_combo.setCurrentIndex(idx)
                return

    def _refresh_theme_labels(self):
        active_lang = self._active_language()
        self.theme_combo.setItemText(0, tr("theme_dark", active_lang))
        self.theme_combo.setItemText(1, tr("theme_light", active_lang))

    def _browse_icon(self):
        icon = QIcon.fromTheme("folder-open")
        fallback = icon.isNull()
        if fallback:
            icon = self.style().standardIcon(self.style().StandardPixmap.SP_DirOpenIcon)
        if self.theme == "dark" and fallback:
            icon = self._tint_icon(icon, QColor("#E4E4E4"))
        return icon

    @staticmethod
    def _tint_icon(icon, color):
        tinted = QIcon()
        for size in (14, 16, 20, 24):
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

    def _active_language(self):
        return self.language_combo.currentData() or self.language

    def load_config(self):
        """Load values from config."""
        config = self.settings.get_config()
        if config:
            self.iverilog_entry.setText(config.get("iverilog_path", ""))
            self.gtkwave_entry.setText(config.get("gtkwave_path", ""))
            self._set_language_combo(normalize_lang(config.get("language", self.language)))
            self._set_theme_combo(config.get("theme", self.theme))
            self.update_auto_check.setChecked(config.get("update_auto_check", True))
            self.update_include_prerelease.setChecked(config.get("update_include_prerelease", False))

    def save_config(self):
        """Save current values to config file."""
        selected_language = self._active_language()
        self.settings.update_config(
            {
                "iverilog_path": self.iverilog_entry.text(),
                "gtkwave_path": self.gtkwave_entry.text(),
                "language": selected_language,
                "theme": self.theme_combo.currentData() or "dark",
                "update_auto_check": self.update_auto_check.isChecked(),
                "update_include_prerelease": self.update_include_prerelease.isChecked(),
            }
        )

        QMessageBox.information(
            self,
            tr("config_saved_title", selected_language),
            tr("config_saved_body", selected_language),
        )
        self.accept()

    def check_updates_now(self):
        """Run manual update check and open release page when available."""
        lang = self._active_language()
        result = check_for_updates(
            current_version=get_current_version(),
            include_prerelease=self.update_include_prerelease.isChecked(),
        )

        if not result.get("ok"):
            QMessageBox.warning(
                self,
                tr("popup_warning_title", lang),
                tr("update_check_failed", lang, error=result.get("error", "unknown")),
            )
            return

        if not result.get("update_available"):
            QMessageBox.information(
                self,
                tr("popup_info_title", lang),
                tr("update_not_available", lang, version=result.get("current_version", "?")),
            )
            return

        should_open = QMessageBox.question(
            self,
            tr("update_available_title", lang),
            tr(
                "update_available_body",
                lang,
                current=result.get("current_version", "?"),
                latest=result.get("latest_version", "?"),
            ),
        )
        if should_open == QMessageBox.StandardButton.Yes:
            webbrowser.open(result.get("release_url", ""))

    def select_executable(self, program_name):
        """Open a file dialog to select executable path."""
        active_lang = self._active_language()
        default_dir = os.path.expanduser("~")
        filters = (
            f"{tr('config_executables', active_lang)} (*.exe *.bin *.sh);;"
            f"{tr('config_all_files', active_lang)} (*.*)"
        )
        file_selected, _ = QFileDialog.getOpenFileName(
            self,
            tr("config_select_exec", active_lang, program=program_name),
            default_dir,
            filters,
        )
        if file_selected:
            if program_name == "iverilog":
                self.iverilog_entry.setText(file_selected)
            else:
                self.gtkwave_entry.setText(file_selected)
