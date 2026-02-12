"""Configuration dialog for tool paths and UI language."""
import os

# pylint: disable=no-name-in-module
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
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

APP_NAME = "BenchSim"
LEGACY_APP_NAMES = ["VerilogSimulator"]


class ConfigDialog(QDialog):
    """Dialog window for configuring tool paths and language."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = SettingsManager(APP_NAME, legacy_app_names=LEGACY_APP_NAMES)
        self.language = normalize_lang(self.settings.get_config().get("language", "en"))

        self.setGeometry(200, 200, 560, 230)
        self.setWindowTitle(tr("config_title", self.language))

        layout = QVBoxLayout()

        iverilog_label = QLabel(tr("config_iverilog", self.language))
        iverilog_layout = QHBoxLayout()
        self.iverilog_entry = QLineEdit()
        self.iverilog_button = QPushButton()
        self.iverilog_button.setIcon(QIcon.fromTheme("folder-open"))
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
        self.gtkwave_button.setIcon(QIcon.fromTheme("folder-open"))
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
        layout.addWidget(language_label)
        layout.addWidget(self.language_combo)

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

    def load_config(self):
        """Load values from config."""
        config = self.settings.get_config()
        if config:
            self.iverilog_entry.setText(config.get("iverilog_path", ""))
            self.gtkwave_entry.setText(config.get("gtkwave_path", ""))
            self._set_language_combo(normalize_lang(config.get("language", self.language)))

    def save_config(self):
        """Save current values to config file."""
        selected_language = self.language_combo.currentData() or "en"
        self.settings.update_config(
            {
                "iverilog_path": self.iverilog_entry.text(),
                "gtkwave_path": self.gtkwave_entry.text(),
                "language": selected_language,
            }
        )

        QMessageBox.information(
            self,
            tr("config_saved_title", selected_language),
            tr("config_saved_body", selected_language),
        )
        self.accept()

    def select_executable(self, program_name):
        """Open a file dialog to select executable path."""
        active_lang = self.language_combo.currentData() or self.language
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
