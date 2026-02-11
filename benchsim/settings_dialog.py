"""Configuration dialog for selecting tool paths (Icarus Verilog and GTKWave)."""
import os

# pylint: disable=no-name-in-module
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QLineEdit, QMessageBox, QHBoxLayout, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from .settings_manager import SettingsManager

APP_NAME = "BenchSim"
LEGACY_APP_NAMES = ["VerilogSimulator"]

class ConfigDialog(QDialog):
    """Dialog window for configuring tool paths (Icarus Verilog and GTKWave).

    Allows users to select and save the paths for required executables.
    The configuration is stored in a JSON file.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Configure Tool Paths"))
        self.setGeometry(200, 200, 500, 200)

        layout = QVBoxLayout()

        self.settings = SettingsManager(APP_NAME, legacy_app_names=LEGACY_APP_NAMES)

        # Iverilog Path
        iverilog_layout = QHBoxLayout()
        iverilog_label = QLabel(self.tr("Icarus Verilog (iverilog) Path"))
        self.iverilog_entry = QLineEdit()
        self.iverilog_button = QPushButton()
        self.iverilog_button.setIcon(QIcon.fromTheme("folder-open"))
        self.iverilog_button.setStyleSheet("color: white;")
        self.iverilog_button.setFixedWidth(30)
        self.iverilog_button.clicked.connect(lambda: self.select_executable("iverilog"))
        iverilog_layout.addWidget(self.iverilog_entry)
        iverilog_layout.addWidget(self.iverilog_button)
        layout.addWidget(iverilog_label)
        layout.addLayout(iverilog_layout)

        # GTKWave Path
        gtkwave_layout = QHBoxLayout()
        gtkwave_label = QLabel(self.tr("GTKWave Path"))
        self.gtkwave_entry = QLineEdit()
        self.gtkwave_button = QPushButton()
        self.gtkwave_button.setIcon(QIcon.fromTheme("folder-open"))
        self.gtkwave_button.setStyleSheet("color: white;")
        self.gtkwave_button.setFixedWidth(30)
        self.gtkwave_button.clicked.connect(lambda: self.select_executable("gtkwave"))
        gtkwave_layout.addWidget(self.gtkwave_entry)
        gtkwave_layout.addWidget(self.gtkwave_button)
        layout.addWidget(gtkwave_label)
        layout.addLayout(gtkwave_layout)

        layout.addSpacing(15)
        self.save_button = QPushButton(self.tr("Save"))
        self.save_button.clicked.connect(self.save_config)
        layout.addWidget(self.save_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
        self.load_config()

    def load_config(self):
        """Load the paths from the config file, if it exists."""
        config = self.settings.get_config()
        if config:
            self.iverilog_entry.setText(config.get("iverilog_path", ""))
            self.gtkwave_entry.setText(config.get("gtkwave_path", ""))

    def save_config(self):
        """Save the current configuration values to the config file."""        
        config = {
            "iverilog_path": self.iverilog_entry.text(),
            "gtkwave_path": self.gtkwave_entry.text()
        }
        self.settings.update_config(config)

        QMessageBox.information(
            self,
            self.tr("Settings Saved"),
            self.tr("The configuration has been saved successfully."))
        self.accept()

    def select_executable(self, program_name):
        """Open a file dialog to select the executable path for a given program."""
        default_dir = os.path.expanduser("~")
        filters = f"{self.tr('Executables')} (*.exe *.bin *.sh);;{self.tr('All Files')} (*.*)"
        file_selected, _ = QFileDialog.getOpenFileName(
            self,
            self.tr(f"Select {program_name}"),
            default_dir,
            filters
        )
        if file_selected:
            if program_name == "iverilog":
                self.iverilog_entry.setText(file_selected)
            else:
                self.gtkwave_entry.setText(file_selected)
