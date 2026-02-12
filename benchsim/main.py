"""Main Qt application for Verilog simulation workflow."""
import os
from pathlib import Path

# pylint: disable=no-name-in-module
from PyQt6.QtGui import QGuiApplication, QIcon, QKeySequence
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .editor import VerilogEditor
from .i18n import normalize_lang, tr
from .message_dispatcher import MessageDispatcher
from .settings_dialog import ConfigDialog
from .settings_manager import SettingsManager
from .simulation_manager import SimulationManager
from .updater import check_for_updates as check_updates_remote, get_current_version

APP_NAME = "BenchSim"
LEGACY_APP_NAMES = ["VerilogSimulator"]


def get_app_icon(base_dir):
    """Return a suitable app icon for current platform."""
    icon_candidates = [
        base_dir / "sim.png",  # Better for Linux launchers/window docks.
        base_dir / "sim.ico",  # Windows executable/window icon.
    ]
    for candidate in icon_candidates:
        if candidate.is_file():
            return QIcon(str(candidate))
    return QIcon()


class BenchSimApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.current_tb_file = None
        self.available_tb_files = []
        self.base_dir = Path(__file__).resolve().parent

        self.simulator = SimulationManager()
        self.settings = SettingsManager(APP_NAME, legacy_app_names=LEGACY_APP_NAMES)
        self.language = normalize_lang(self.settings.get_config().get("language", "en"))

        self.setWindowIcon(get_app_icon(self.base_dir))

        theme_path = self.base_dir / "themes" / "dark.qss"
        self.setStyleSheet(self.load_stylesheet(theme_path))

        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-family: Arial, sans-serif; font-size: 14px;")
        status_bar.addWidget(self.status_label)

        self.save_button = QPushButton(QIcon.fromTheme("document-save"), "")
        self.save_button.setEnabled(False)
        self.save_button.setShortcut(QKeySequence.StandardKey.Save)
        self.save_button.clicked.connect(self.save_tb_file)

        self.validate_button = QPushButton(QIcon.fromTheme("dialog-ok-apply"), "")
        self.validate_button.clicked.connect(self.validate_project)

        self.sim_button = QPushButton(QIcon.fromTheme("media-playback-start"), "")
        self.sim_button.setShortcut(QKeySequence("Ctrl+R"))
        self.sim_button.clicked.connect(self.run_simulation)

        status_bar.addPermanentWidget(self.save_button)
        status_bar.addPermanentWidget(self.validate_button)
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
        self.folder_entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("", "auto")
        self.mode_combo.addItem("", "icestudio")
        self.mode_combo.addItem("", "generic")
        self.mode_combo.currentIndexChanged.connect(self.reload_verilog_folder)

        self.tb_combo = QComboBox()
        self.tb_combo.currentIndexChanged.connect(self.tb_selection_changed)

        self.folder_button = QToolButton()
        self.folder_button.setIcon(QIcon.fromTheme("folder-open"))
        self.folder_button.clicked.connect(self.select_folder)

        self.reload_button = QToolButton()
        self.reload_button.setIcon(QIcon.fromTheme("view-refresh"))
        self.reload_button.clicked.connect(self.reload_verilog_folder)

        self.config_button = QToolButton()
        self.config_button.setIcon(QIcon.fromTheme("settings"))
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
            language=self.language,
            popup_on={"error": True, "warning": False, "success": False, "log": False},
            toast_on={"error": False, "warning": True, "success": True, "log": False},
        )

        self.load_config()
        self.apply_language()
        self.editor.file_changed.connect(self.tb_changed)
        QTimer.singleShot(1200, self.maybe_check_updates_on_startup)

    @staticmethod
    def load_stylesheet(theme_path):
        with open(theme_path, "r", encoding="utf-8") as file:
            return file.read()

    def apply_language(self):
        self.setWindowTitle(tr("app_name", self.language))
        self.status_label.setText(tr("status_clean", self.language))
        self.save_button.setText(tr("btn_save", self.language))
        self.save_button.setToolTip(tr("tooltip_save", self.language))
        self.validate_button.setText(tr("btn_validate", self.language))
        self.validate_button.setToolTip(tr("tooltip_validate", self.language))
        self.sim_button.setText(tr("btn_simulate", self.language))
        self.sim_button.setToolTip(tr("tooltip_simulate", self.language))

        self.folder_entry.setPlaceholderText(tr("placeholder_folder", self.language))
        self.mode_combo.setItemText(0, tr("mode_auto", self.language))
        self.mode_combo.setItemText(1, tr("mode_icestudio", self.language))
        self.mode_combo.setItemText(2, tr("mode_generic", self.language))
        self.mode_combo.setToolTip(tr("tooltip_mode", self.language))
        self.tb_combo.setToolTip(tr("tooltip_tb", self.language))
        self.folder_button.setToolTip(tr("tooltip_select_folder", self.language))
        self.reload_button.setToolTip(tr("tooltip_reload", self.language))
        self.config_button.setText(tr("settings_button", self.language))
        self.config_button.setToolTip(tr("tooltip_settings", self.language))
        self.dispatcher.set_language(self.language)

    def _set_mode_value(self, mode_value):
        for index in range(self.mode_combo.count()):
            if self.mode_combo.itemData(index) == mode_value:
                self.mode_combo.setCurrentIndex(index)
                return

    def _current_mode(self):
        return self.mode_combo.currentData()

    def _selected_tb_path(self):
        if self.tb_combo.currentIndex() < 0:
            return None
        return self.tb_combo.currentData()

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
        self.status_label.setText(tr("status_saved", self.language))
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

        self.console.append(
            tr(
                "project_loaded",
                self.language,
                mode=discovery["effective_mode"],
                tb_count=len(self.available_tb_files),
                source_count=len(discovery["source_files"]),
            )
        )

    def validate_project(self):
        folder_path = self.folder_entry.text().strip()
        tb_path = self._selected_tb_path()
        success, messages, plan = self.simulator.build_compile_plan(
            folder=folder_path,
            mode=self._current_mode(),
            tb_file=tb_path,
            require_tools=True,
        )
        for message in messages:
            self.dispatcher.handle_message(message)
        if not success:
            return

        self.console.clear()
        self.console.append(tr("validation_preview_title", self.language))
        self.console.append(
            tr(
                "validation_preview_meta",
                self.language,
                mode=plan["mode"],
                tb=os.path.basename(plan["selected_tb"]) if plan["selected_tb"] else "N/A",
                count=len(plan["compile_files"]),
            )
        )
        for file_path in plan["compile_files"]:
            self.console.append(file_path)

        self.dispatcher.handle_message(
            {
                "type": "success",
                "message": tr(
                    "validation_success",
                    self.language,
                    mode=plan["mode"],
                    tb=os.path.basename(plan["selected_tb"]) if plan["selected_tb"] else "N/A",
                    count=len(plan["compile_files"]),
                ),
                "extras": ["toast"],
            }
        )

    def run_simulation(self):
        self.console.clear()
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.console.append(tr("error_no_screen", self.language))
            return

        self.save_tb_file()

        folder_path = self.folder_entry.text().strip()
        tb_path = self._selected_tb_path()
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
        if config_dialog.exec():
            self.language = normalize_lang(self.settings.get_config().get("language", "en"))
            self.apply_language()

    def maybe_check_updates_on_startup(self):
        """Check for updates when enabled in settings."""
        cfg = self.settings.get_config()
        if not cfg.get("update_auto_check", True):
            return
        self.check_for_updates(silent_errors=True)

    def check_for_updates(self, silent_errors=False):
        """Check GitHub releases and prompt user when an update is available."""
        cfg = self.settings.get_config()
        include_prerelease = cfg.get("update_include_prerelease", False)
        result = check_updates_remote(
            current_version=get_current_version(),
            include_prerelease=include_prerelease,
        )

        if not result.get("ok"):
            if not silent_errors:
                QMessageBox.warning(
                    self,
                    tr("popup_warning_title", self.language),
                    tr("update_check_failed", self.language, error=result.get("error", "unknown")),
                )
            return

        if not result.get("update_available"):
            return

        answer = QMessageBox.question(
            self,
            tr("update_available_title", self.language),
            tr(
                "update_available_body",
                self.language,
                current=result.get("current_version", "?"),
                latest=result.get("latest_version", "?"),
            ),
        )
        if answer == QMessageBox.StandardButton.Yes:
            import webbrowser  # Local import to avoid startup overhead.
            webbrowser.open(result.get("release_url", ""))

    def load_config(self):
        config = self.settings.get_config()
        folder_path = config.get("verilog_folder", "") if config else ""
        project_mode = config.get("project_mode", "auto") if config else "auto"
        selected_tb = config.get("selected_tb", "") if config else ""
        self.language = normalize_lang(config.get("language", "en")) if config else self.language

        self.folder_entry.setText(folder_path)
        self._set_mode_value(project_mode)
        self._refresh_project(preserve_tb=selected_tb)

    def reload_verilog_folder(self):
        self._refresh_project(preserve_tb=self.current_tb_file)

    def tb_selection_changed(self):
        tb_path = self._selected_tb_path()
        if tb_path:
            self._load_tb_file(tb_path)

    def tb_changed(self):
        self.status_label.setText(tr("status_dirty", self.language))
        self.save_button.setEnabled(True)

    def save_tb_file(self):
        if not self.current_tb_file:
            return

        target_file = self.current_tb_file
        backup_file = f"{target_file}.bak"
        temp_file = f"{target_file}.tmp"

        # Keep a backup copy of the last saved version without removing the source file.
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as src:
                original_content = src.read()
            with open(backup_file, "w", encoding="utf-8") as bak:
                bak.write(original_content)

        # Atomic save to avoid partial writes or stale content on refresh.
        with open(temp_file, "w", encoding="utf-8") as file:
            file.write(self.editor.text())
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_file, target_file)

        self.save_button.setEnabled(False)
        self.status_label.setText(tr("status_saved", self.language))

    def select_folder(self):
        default_dir = self.folder_entry.text() or os.path.expanduser("~")
        folder_selected = QFileDialog.getExistingDirectory(
            self,
            tr("dialog_select_folder", self.language),
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
    app.setApplicationName("benchsim")
    app.setApplicationDisplayName("BenchSim")
    app.setOrganizationName("BenchSim")
    if hasattr(app, "setDesktopFileName"):
        app.setDesktopFileName("benchsim")
    app.setWindowIcon(get_app_icon(Path(__file__).resolve().parent))
    window = BenchSimApp()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
