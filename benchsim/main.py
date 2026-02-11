"""Main Qt application for Verilog simulation workflow."""
import os
from pathlib import Path

# pylint: disable=no-name-in-module
from PyQt6.QtGui import QGuiApplication, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .editor import VerilogEditor
from .message_dispatcher import MessageDispatcher
from .settings_dialog import ConfigDialog
from .settings_manager import SettingsManager
from .simulation_manager import SimulationManager

APP_NAME = "BenchSim"
LEGACY_APP_NAMES = ["VerilogSimulator"]


class BenchSimApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.current_tb_file = None
        self.available_tb_files = []
        self.base_dir = Path(__file__).resolve().parent

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(self.base_dir / "sim.ico")))

        theme_path = self.base_dir / "themes" / "dark.qss"
        self.setStyleSheet(self.load_stylesheet(theme_path))

        self.simulator = SimulationManager()
        self.settings = SettingsManager(APP_NAME, legacy_app_names=LEGACY_APP_NAMES)

        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self.status_label = QLabel("Sin cambios")
        self.status_label.setStyleSheet("font-family: Arial, sans-serif; font-size: 14px;")
        status_bar.addWidget(self.status_label)

        self.save_button = QPushButton(QIcon.fromTheme("document-save"), "Guardar")
        self.save_button.setEnabled(False)
        self.save_button.setToolTip("Guardar cambios (Ctrl+S)")
        self.save_button.setShortcut(QKeySequence.StandardKey.Save)
        self.save_button.clicked.connect(self.save_tb_file)

        self.sim_button = QPushButton(QIcon.fromTheme("media-playback-start"), "Guardar y Simular")
        self.sim_button.setToolTip("Guardar y Ejecutar simulacion (Ctrl+R)")
        self.sim_button.setShortcut(QKeySequence("Ctrl+R"))
        self.sim_button.clicked.connect(self.run_simulation)

        status_bar.addPermanentWidget(self.save_button)
        status_bar.addPermanentWidget(self.sim_button)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()

        toolbar = QFrame()
        toolbar.setStyleSheet(self.load_stylesheet(theme_path))

        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 4, 10, 4)
        toolbar_layout.setSpacing(10)

        self.folder_entry = QLineEdit()
        self.folder_entry.setPlaceholderText("Selecciona la carpeta raiz del proyecto...")
        self.folder_entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Auto", "auto")
        self.mode_combo.addItem("Icestudio", "icestudio")
        self.mode_combo.addItem("Generico", "generic")
        self.mode_combo.setToolTip("Modo de deteccion de archivos fuente")
        self.mode_combo.currentIndexChanged.connect(self.reload_verilog_folder)

        self.tb_combo = QComboBox()
        self.tb_combo.setToolTip("Testbench a editar y simular")
        self.tb_combo.currentIndexChanged.connect(self.tb_selection_changed)

        self.folder_button = QToolButton()
        self.folder_button.setIcon(QIcon.fromTheme("folder-open"))
        self.folder_button.setToolTip("Seleccionar carpeta")
        self.folder_button.clicked.connect(self.select_folder)

        self.reload_button = QToolButton()
        self.reload_button.setIcon(QIcon.fromTheme("view-refresh"))
        self.reload_button.setToolTip("Recargar archivos del proyecto")
        self.reload_button.clicked.connect(self.reload_verilog_folder)

        self.config_button = QToolButton()
        self.config_button.setText("CFG")
        self.config_button.setIcon(QIcon.fromTheme("settings"))
        self.config_button.setToolTip("Configuracion de simulador")
        self.config_button.clicked.connect(self.open_config_dialog)

        toolbar_layout.addWidget(self.folder_entry)
        toolbar_layout.addWidget(self.mode_combo)
        toolbar_layout.addWidget(self.tb_combo)
        toolbar_layout.addWidget(self.folder_button)
        toolbar_layout.addWidget(self.reload_button)
        toolbar_layout.addWidget(self.config_button)
        layout.addWidget(toolbar)

        layout.addSpacing(15)

        self.editor = VerilogEditor(self)
        layout.addWidget(self.editor, 4)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console, 1)

        central_widget.setLayout(layout)

        self.dispatcher = MessageDispatcher(
            console_widget=self.console,
            parent_window=self,
            popup_on={"error": True, "warning": False, "success": False, "log": False},
            toast_on={"error": False, "warning": True, "success": True, "log": False},
        )

        self.load_config()
        self.editor.file_changed.connect(self.tb_changed)

    @staticmethod
    def load_stylesheet(theme_path):
        with open(theme_path, "r", encoding="utf-8") as file:
            return file.read()

    def _set_mode_value(self, mode_value):
        for index in range(self.mode_combo.count()):
            if self.mode_combo.itemData(index) == mode_value:
                self.mode_combo.setCurrentIndex(index)
                return

    def _current_mode(self):
        return self.mode_combo.currentData()

    def _select_tb_in_combo(self, tb_path):
        if not tb_path:
            return
        for index in range(self.tb_combo.count()):
            if self.tb_combo.itemData(index) == tb_path:
                self.tb_combo.setCurrentIndex(index)
                return

    def _load_tb_file(self, tb_path):
        if not tb_path or not os.path.isfile(tb_path):
            return
        with open(tb_path, "r", encoding="utf-8") as verilog_file:
            self.editor.set_text_safely(verilog_file.read())
        self.current_tb_file = tb_path
        self.status_label.setText("Cambios guardados")
        self.save_button.setEnabled(False)

    def _refresh_project(self, preserve_tb=None):
        folder_path = self.folder_entry.text().strip()
        if not folder_path or not os.path.isdir(folder_path):
            self.available_tb_files = []
            self.tb_combo.clear()
            self.current_tb_file = None
            self.editor.set_text_safely("")
            return

        discovery = self.simulator.discover_project_files(folder_path, mode=self._current_mode())
        self.available_tb_files = discovery["tb_files"]

        self.tb_combo.blockSignals(True)
        self.tb_combo.clear()
        for tb_file in self.available_tb_files:
            self.tb_combo.addItem(os.path.basename(tb_file), tb_file)
        self.tb_combo.blockSignals(False)

        selected_tb = preserve_tb if preserve_tb in self.available_tb_files else discovery["preferred_tb"]
        if selected_tb:
            self._select_tb_in_combo(selected_tb)
            self._load_tb_file(selected_tb)

        source_count = len(discovery["source_files"])
        scope_mode = discovery["effective_mode"]
        self.console.append(
            f"<b>Proyecto cargado</b>: modo={scope_mode}, tb={len(self.available_tb_files)}, fuentes={source_count}"
        )

    def run_simulation(self):
        self.console.clear()
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.console.append("No se pudo determinar el tamano de pantalla para GTKWave.")
            return

        self.save_tb_file()

        folder_path = self.folder_entry.text().strip()
        tb_path = self.tb_combo.currentData() if self.tb_combo.currentIndex() >= 0 else None
        success, messages = self.simulator.run_simulation(
            screen.availableGeometry(),
            folder=folder_path,
            mode=self._current_mode(),
            tb_file=tb_path,
        )
        for message in messages:
            self.dispatcher.handle_message(message)

        if success:
            self.settings.update_config(
                {
                    "verilog_folder": folder_path,
                    "project_mode": self._current_mode(),
                    "selected_tb": tb_path or "",
                }
            )

    def open_config_dialog(self):
        config_dialog = ConfigDialog(self)
        config_dialog.exec()

    def load_config(self):
        config = self.settings.get_config()
        folder_path = config.get("verilog_folder", "") if config else ""
        project_mode = config.get("project_mode", "auto") if config else "auto"
        selected_tb = config.get("selected_tb", "") if config else ""

        self.folder_entry.setText(folder_path)
        self._set_mode_value(project_mode)
        self._refresh_project(preserve_tb=selected_tb)

    def reload_verilog_folder(self):
        self._refresh_project(preserve_tb=self.current_tb_file)

    def tb_selection_changed(self):
        tb_path = self.tb_combo.currentData() if self.tb_combo.currentIndex() >= 0 else None
        if tb_path:
            self._load_tb_file(tb_path)

    def tb_changed(self):
        self.status_label.setText("Cambios sin guardar")
        self.save_button.setEnabled(True)

    def save_tb_file(self):
        if not self.current_tb_file:
            return

        backup_file = self.current_tb_file + ".bak"
        if os.path.exists(self.current_tb_file):
            if os.path.exists(backup_file):
                os.remove(backup_file)
            os.rename(self.current_tb_file, backup_file)

        with open(self.current_tb_file, "w", encoding="utf-8") as file:
            file.write(self.editor.text())

        self.save_button.setEnabled(False)
        self.status_label.setText("Cambios guardados")

    def select_folder(self):
        default_dir = self.folder_entry.text() or os.path.expanduser("~")
        folder_selected = QFileDialog.getExistingDirectory(
            self,
            "Selecciona una carpeta",
            default_dir,
        )
        if not folder_selected:
            return

        self.folder_entry.setText(folder_selected)
        self._refresh_project()
        self.settings.update_config(
            {
                "verilog_folder": folder_selected,
                "project_mode": self._current_mode(),
                "selected_tb": self.current_tb_file or "",
            }
        )

    def closeEvent(self, event):
        """Close GTKWave process when the main window closes."""
        self.simulator.close_gtkwave()
        event.accept()


def main():
    app = QApplication([])
    window = BenchSimApp()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
