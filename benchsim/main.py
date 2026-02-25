"""Main Qt application for Verilog simulation workflow."""
import os
import sys
from pathlib import Path

# pylint: disable=no-name-in-module
from PyQt6.QtGui import QGuiApplication, QIcon, QKeySequence, QShortcut
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
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
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

try:
    from .editor import VerilogEditor
    from .editor_search_controller import EditorSearchController
    from .external_change_controller import ExternalTBChangeController
    from .i18n import normalize_lang, tr
    from .simulation_flow_controller import SimulationFlowController
    from .ui_theme_controller import UIThemeController
    from .update_controller import UpdateController
    from .message_dispatcher import MessageDispatcher
    from .linux_desktop_controller import LinuxDesktopController
    from .settings_dialog import ConfigDialog
    from .settings_manager import SettingsManager
    from .simulation_manager import SimulationManager
    from .project_load_controller import ProjectLoadController
    from .project_selection_controller import ProjectSelectionController
    from .problems_controller import ProblemsController
    from .tb_file_controller import TBFileController
except ImportError:
    from benchsim.editor import VerilogEditor
    from benchsim.editor_search_controller import EditorSearchController
    from benchsim.external_change_controller import ExternalTBChangeController
    from benchsim.i18n import normalize_lang, tr
    from benchsim.simulation_flow_controller import SimulationFlowController
    from benchsim.ui_theme_controller import UIThemeController
    from benchsim.update_controller import UpdateController
    from benchsim.message_dispatcher import MessageDispatcher
    from benchsim.linux_desktop_controller import LinuxDesktopController
    from benchsim.settings_dialog import ConfigDialog
    from benchsim.settings_manager import SettingsManager
    from benchsim.simulation_manager import SimulationManager
    from benchsim.project_load_controller import ProjectLoadController
    from benchsim.project_selection_controller import ProjectSelectionController
    from benchsim.problems_controller import ProblemsController
    from benchsim.tb_file_controller import TBFileController

APP_NAME = "BenchSim"


def get_resource_base_dir():
    """Return resource base directory for source and frozen builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "benchsim"
    return Path(__file__).resolve().parent


def get_app_icon(base_dir):
    """Return a suitable app icon for current platform."""
    icon_candidates = [
        base_dir / "benchsim.png",  # Better for Linux launchers/window docks.
        base_dir / "benchsim.ico",  # Windows executable/window icon.
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
        self.external_change_controller = ExternalTBChangeController(self)
        self.external_change_controller.pending_changed.connect(self._on_external_conflict_pending_changed)
        self.external_change_pending = False
        self.base_dir = get_resource_base_dir()

        self.simulator = SimulationManager()
        self.settings = SettingsManager(APP_NAME)
        cfg = self.settings.get_config()
        self.language = normalize_lang(cfg.get("language", "en"))
        self.theme = cfg.get("theme", "dark")
        self.editor_font_size = self._sanitize_font_size(cfg.get("editor_font_size", 12))

        self.setWindowIcon(get_app_icon(self.base_dir))

        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-family: Arial, sans-serif; font-size: 14px;")
        status_bar.addWidget(self.status_label)

        self.save_button = QPushButton(QIcon.fromTheme("document-save"), "")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_tb_file)

        self.sim_button = QPushButton(QIcon.fromTheme("media-playback-start"), "")
        self.sim_button.clicked.connect(self.run_simulation)

        status_bar.addPermanentWidget(self.save_button)
        status_bar.addPermanentWidget(self.sim_button)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()

        toolbar = QFrame()

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

        self.recent_combo = QComboBox()
        self.recent_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.recent_combo.currentIndexChanged.connect(self.open_recent_project)

        self.folder_button = QToolButton()
        self.folder_button.clicked.connect(self.select_folder)

        self.reload_button = QToolButton()
        self.reload_button.clicked.connect(self.reload_verilog_folder)

        self.validate_tool_button = QToolButton()
        self.validate_tool_button.clicked.connect(self.validate_project)

        self.config_button = QToolButton()
        self.config_button.clicked.connect(self.open_config_dialog)

        toolbar_layout.addWidget(self.folder_entry)
        toolbar_layout.addWidget(self.recent_combo)
        toolbar_layout.addWidget(self.mode_combo)
        toolbar_layout.addWidget(self.tb_combo)
        toolbar_layout.addWidget(self.folder_button)
        toolbar_layout.addWidget(self.reload_button)
        toolbar_layout.addWidget(self.validate_tool_button)
        toolbar_layout.addWidget(self.config_button)
        layout.addWidget(toolbar)

        self.search_bar = QFrame()
        search_layout = QHBoxLayout(self.search_bar)
        search_layout.setContentsMargins(10, 2, 10, 2)
        search_layout.setSpacing(8)

        self.find_label = QLabel("")
        self.find_input = QLineEdit()

        self.replace_label = QLabel("")
        self.replace_input = QLineEdit()

        self.case_checkbox = QCheckBox("")
        self.whole_word_checkbox = QCheckBox("")

        self.find_prev_button = QPushButton("")
        self.find_prev_button.clicked.connect(lambda: self.search_controller.find_prev())
        self.find_next_button = QPushButton("")
        self.find_next_button.clicked.connect(lambda: self.search_controller.find_next())
        self.replace_button = QPushButton("")
        self.replace_button.clicked.connect(lambda: self.search_controller.replace_current())
        self.replace_all_button = QPushButton("")
        self.replace_all_button.clicked.connect(lambda: self.search_controller.replace_all())
        self.close_search_button = QToolButton()
        self.close_search_button.setIcon(QIcon.fromTheme("window-close"))
        self.close_search_button.clicked.connect(lambda: self.search_controller.hide_search_bar())

        search_layout.addWidget(self.find_label)
        search_layout.addWidget(self.find_input, 2)
        search_layout.addWidget(self.replace_label)
        search_layout.addWidget(self.replace_input, 2)
        search_layout.addWidget(self.case_checkbox)
        search_layout.addWidget(self.whole_word_checkbox)
        search_layout.addWidget(self.find_prev_button)
        search_layout.addWidget(self.find_next_button)
        search_layout.addWidget(self.replace_button)
        search_layout.addWidget(self.replace_all_button)
        search_layout.addWidget(self.close_search_button)
        layout.addWidget(self.search_bar)
        self.search_bar.hide()

        self.external_change_bar = QFrame()
        self.external_change_bar.setObjectName("externalChangeBar")
        self.external_change_bar.setVisible(False)
        self.external_change_bar.setFrameShape(QFrame.Shape.NoFrame)
        external_layout = QHBoxLayout(self.external_change_bar)
        external_layout.setContentsMargins(8, 3, 8, 3)
        external_layout.setSpacing(6)
        self.external_change_label = QLabel("")
        self.external_change_label.setWordWrap(True)
        self.external_reload_button = QPushButton("")
        self.external_reload_button.clicked.connect(self._reload_external_tb)
        self.external_keep_button = QPushButton("")
        self.external_keep_button.clicked.connect(self._keep_local_tb)
        external_layout.addWidget(self.external_change_label, 1)
        external_layout.addWidget(self.external_reload_button)
        external_layout.addWidget(self.external_keep_button)
        layout.addWidget(self.external_change_bar)

        layout.addSpacing(15)

        self.editor = VerilogEditor(self)
        self.editor.set_editor_font_size(self.editor_font_size)
        self.editor.zoom_requested.connect(self._on_editor_zoom_requested)
        self.editor.zoom_reset_requested.connect(self.reset_editor_font_size)
        layout.addWidget(self.editor, 4)

        self.search_controller = EditorSearchController(
            editor=self.editor,
            search_bar=self.search_bar,
            find_label=self.find_label,
            find_input=self.find_input,
            replace_label=self.replace_label,
            replace_input=self.replace_input,
            case_checkbox=self.case_checkbox,
            whole_word_checkbox=self.whole_word_checkbox,
            find_prev_button=self.find_prev_button,
            find_next_button=self.find_next_button,
            replace_button=self.replace_button,
            replace_all_button=self.replace_all_button,
            close_search_button=self.close_search_button,
            status_label=self.status_label,
            save_button=self.save_button,
            translate=lambda key, **kwargs: tr(key, self.language, **kwargs),
        )
        self.find_input.returnPressed.connect(lambda: self.search_controller.find_next())
        self.replace_input.returnPressed.connect(lambda: self.search_controller.replace_current())
        self.project_selection_controller = ProjectSelectionController(
            settings=self.settings,
            mode_combo=self.mode_combo,
            tb_combo=self.tb_combo,
            recent_combo=self.recent_combo,
            translate=lambda key, **kwargs: tr(key, self.language, **kwargs),
            open_project_folder=self._open_project_folder_from_recent,
            get_current_tb_path=lambda: self.current_tb_file,
        )
        self.tb_file_controller = TBFileController(
            editor=self.editor,
            status_label=self.status_label,
            save_button=self.save_button,
            external_change_controller=self.external_change_controller,
            on_hide_external_banner=self._hide_external_change_banner,
        )
        self.console = QTextBrowser()
        self.console.setReadOnly(True)
        self.console.setOpenLinks(False)
        self.console.setOpenExternalLinks(False)
        self.console.anchorClicked.connect(self._handle_console_link)
        layout.addWidget(self.console, 1)

        self.project_load_controller = ProjectLoadController(
            simulator=self.simulator,
            tb_combo=self.tb_combo,
            folder_path_getter=lambda: self.folder_entry.text(),
            mode_getter=lambda: self.project_selection_controller.current_mode(),
            reset_problem_index=self._reset_problem_index,
            clear_editor=lambda: self.editor.set_text_safely(""),
            clear_external_change_state=self._clear_current_tb_state,
            load_tb_file=self._load_tb_file,
            select_tb_in_combo=self.project_selection_controller.select_tb_in_combo,
            append_console=lambda msg: self.console.append(msg),
            translate=tr,
            language_getter=lambda: self.language,
        )
        self.problems_controller = ProblemsController(
            console_widget=self.console,
            translate=tr,
            language_getter=lambda: self.language,
        )

        central_widget.setLayout(layout)

        self.dispatcher = MessageDispatcher(
            console_widget=self.console,
            parent_window=self,
            language=self.language,
            popup_on={"error": True, "warning": False, "success": False, "log": False},
            toast_on={"error": False, "warning": True, "success": True, "log": False},
        )
        self.update_controller = UpdateController(
            settings=self.settings,
            translate=tr,
            language_getter=lambda: self.language,
        )
        self.simulation_flow_controller = SimulationFlowController(
            simulator=self.simulator,
            dispatcher=self.dispatcher,
            settings=self.settings,
            project_selection=self.project_selection_controller,
            folder_path_getter=lambda: self.folder_entry.text(),
            reset_problem_index=self._reset_problem_index,
            ensure_no_external_conflict=self._ensure_no_external_change_conflict,
            save_tb_file=self.save_tb_file,
            get_screen_geometry=self._primary_screen_geometry,
            append_console=lambda msg: self.console.append(msg),
            clear_console=self.console.clear,
            append_problems=self._append_problems_to_console,
            translate=tr,
            language_getter=lambda: self.language,
        )
        self.ui_theme_controller = UIThemeController(
            widget=self,
            base_dir=self.base_dir,
            load_stylesheet=self.load_stylesheet,
            editor=self.editor,
            external_change_bar=self.external_change_bar,
            folder_button=self.folder_button,
            reload_button=self.reload_button,
            validate_tool_button=self.validate_tool_button,
            config_button=self.config_button,
        )
        self.linux_desktop_controller = LinuxDesktopController(
            settings=self.settings,
            base_dir=self.base_dir,
            dispatcher=self.dispatcher,
            translate=tr,
            language_getter=lambda: self.language,
        )

        self.load_config()
        self.project_selection_controller.refresh_recent_projects()
        self.apply_theme()
        self.apply_language()
        self.setup_shortcuts()
        self.editor.file_changed.connect(self.tb_changed)
        QTimer.singleShot(1200, self.maybe_check_updates_on_startup)
        QTimer.singleShot(1600, self.maybe_setup_linux_desktop_entry)

    def _open_project_folder_from_recent(self, folder_path):
        self.folder_entry.setText(folder_path)
        self._refresh_project()

    @staticmethod
    def load_stylesheet(theme_path):
        with open(theme_path, "r", encoding="utf-8") as file:
            return file.read()

    def setup_shortcuts(self):
        """Register window shortcuts that also work while editor has focus."""
        self.shortcut_save = QShortcut(QKeySequence.StandardKey.Save, self)
        self.shortcut_save.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_save.activated.connect(self.save_tb_file)

        self.shortcut_sim = QShortcut(QKeySequence("Ctrl+R"), self)
        self.shortcut_sim.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_sim.activated.connect(self.run_simulation)

        self.shortcut_validate = QShortcut(QKeySequence("Ctrl+Shift+V"), self)
        self.shortcut_validate.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_validate.activated.connect(self.validate_project)

        self.shortcut_open = QShortcut(QKeySequence.StandardKey.Open, self)
        self.shortcut_open.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_open.activated.connect(self.select_folder)

        self.shortcut_reload = QShortcut(QKeySequence("F5"), self)
        self.shortcut_reload.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_reload.activated.connect(self.reload_verilog_folder)

        self.shortcut_settings = QShortcut(QKeySequence("Ctrl+,"), self)
        self.shortcut_settings.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_settings.activated.connect(self.open_config_dialog)

        self.shortcut_find = QShortcut(QKeySequence.StandardKey.Find, self)
        self.shortcut_find.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_find.activated.connect(lambda: self.search_controller.show_find_bar())

        self.shortcut_replace = QShortcut(QKeySequence.StandardKey.Replace, self)
        self.shortcut_replace.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_replace.activated.connect(lambda: self.search_controller.show_replace_bar())

        self.shortcut_find_next = QShortcut(QKeySequence("F3"), self)
        self.shortcut_find_next.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_find_next.activated.connect(lambda: self.search_controller.find_next())

        self.shortcut_find_prev = QShortcut(QKeySequence("Shift+F3"), self)
        self.shortcut_find_prev.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_find_prev.activated.connect(lambda: self.search_controller.find_prev())

        self.shortcut_hide_search = QShortcut(QKeySequence("Escape"), self)
        self.shortcut_hide_search.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_hide_search.activated.connect(lambda: self.search_controller.hide_search_bar())

        self.shortcut_autocomplete = QShortcut(QKeySequence("Ctrl+Space"), self)
        self.shortcut_autocomplete.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_autocomplete.activated.connect(self.editor.trigger_autocomplete)

        self.shortcut_zoom_in_eq = QShortcut(QKeySequence("Ctrl+="), self)
        self.shortcut_zoom_in_eq.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_zoom_in_eq.activated.connect(self.increase_editor_font_size)

        self.shortcut_zoom_in_plus = QShortcut(QKeySequence("Ctrl++"), self)
        self.shortcut_zoom_in_plus.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_zoom_in_plus.activated.connect(self.increase_editor_font_size)

        self.shortcut_zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        self.shortcut_zoom_out.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_zoom_out.activated.connect(self.decrease_editor_font_size)

        self.shortcut_zoom_reset = QShortcut(QKeySequence("Ctrl+0"), self)
        self.shortcut_zoom_reset.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_zoom_reset.activated.connect(self.reset_editor_font_size)

        self.shortcut_zoom_reset_kp = QShortcut(QKeySequence("Ctrl+KP_0"), self)
        self.shortcut_zoom_reset_kp.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_zoom_reset_kp.activated.connect(self.reset_editor_font_size)

    @staticmethod
    def _sanitize_font_size(value):
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = 12
        return max(VerilogEditor.MIN_FONT_SIZE, min(VerilogEditor.MAX_FONT_SIZE, parsed))

    def _set_editor_font_size(self, new_size, persist=True):
        size = self._sanitize_font_size(new_size)
        self.editor.set_editor_font_size(size)
        self.editor_font_size = self.editor.get_editor_font_size()
        self.status_label.setText(tr("status_font_size", self.language, size=self.editor_font_size))
        if persist:
            self.settings.update_config({"editor_font_size": self.editor_font_size})

    def increase_editor_font_size(self):
        self._set_editor_font_size(self.editor.get_editor_font_size() + 1)

    def decrease_editor_font_size(self):
        self._set_editor_font_size(self.editor.get_editor_font_size() - 1)

    def reset_editor_font_size(self):
        self._set_editor_font_size(12)

    def _on_editor_zoom_requested(self, delta):
        self._set_editor_font_size(self.editor.get_editor_font_size() + delta)

    def apply_theme(self):
        self.theme = self.ui_theme_controller.apply_theme(self.theme)

    def apply_language(self):
        self.setWindowTitle(tr("app_name", self.language))
        self.status_label.setText(tr("status_clean", self.language))
        self.save_button.setText(tr("btn_save", self.language))
        self.save_button.setToolTip(tr("tooltip_save", self.language))
        self.sim_button.setText(tr("btn_simulate", self.language))
        self.sim_button.setToolTip(tr("tooltip_simulate", self.language))

        self.folder_entry.setPlaceholderText(tr("placeholder_folder", self.language))
        self.mode_combo.setItemText(0, tr("mode_auto", self.language))
        self.mode_combo.setItemText(1, tr("mode_icestudio", self.language))
        self.mode_combo.setItemText(2, tr("mode_generic", self.language))
        self.mode_combo.setToolTip(tr("tooltip_mode", self.language))
        self.tb_combo.setToolTip(tr("tooltip_tb", self.language))
        self.recent_combo.setToolTip(tr("tooltip_recent_projects", self.language))
        self.folder_button.setToolTip(f"{tr('tooltip_select_folder', self.language)} (Ctrl+O)")
        self.reload_button.setToolTip(f"{tr('tooltip_reload', self.language)} (F5)")
        self.validate_tool_button.setToolTip(f"{tr('tooltip_validate', self.language)} (Ctrl+Shift+V)")
        self.config_button.setText(tr("settings_button", self.language))
        self.config_button.setToolTip(f"{tr('tooltip_settings', self.language)} (Ctrl+,)")

        self.search_controller.apply_language()
        self.external_change_label.setText(tr("external_change_banner", self.language))
        self.external_reload_button.setText(tr("external_change_reload", self.language))
        self.external_keep_button.setText(tr("external_change_keep", self.language))
        self.project_selection_controller.refresh_recent_projects()
        self.dispatcher.set_language(self.language)

    def _set_mode_value(self, mode_value):
        self.project_selection_controller.set_mode_value(mode_value)

    def _current_mode(self):
        return self.project_selection_controller.current_mode()

    def _selected_tb_path(self):
        return self.project_selection_controller.selected_tb_path()

    def _select_tb_in_combo(self, tb_path):
        self.project_selection_controller.select_tb_in_combo(tb_path)

    def _load_tb_file(self, tb_path):
        loaded = self.tb_file_controller.load_tb_file(
            tb_path,
            status_saved_text=tr("status_saved", self.language),
        )
        if loaded:
            self.current_tb_file = tb_path

    def _clear_current_tb_state(self):
        self.current_tb_file = None
        self.external_change_controller.clear_current_tb_file()
        self._hide_external_change_banner()

    def _show_external_change_banner(self):
        self._on_external_conflict_pending_changed(True)
        self.status_label.setText(tr("status_external_pending", self.language))

    def _hide_external_change_banner(self):
        self._on_external_conflict_pending_changed(False)

    def _on_external_conflict_pending_changed(self, pending):
        """Update UI state when external-change conflict is pending/resolved."""
        self.external_change_pending = bool(pending)
        self.external_change_bar.setVisible(self.external_change_pending)
        self.sim_button.setEnabled(not self.external_change_pending)

    def _reload_external_tb(self):
        if not self.current_tb_file:
            return
        self._load_tb_file(self.current_tb_file)
        self.status_label.setText(tr("status_external_reloaded", self.language))

    def _keep_local_tb(self):
        if not self.current_tb_file:
            return
        self.external_change_controller.keep_local_version()
        self._hide_external_change_banner()
        # Persist local buffer immediately to avoid losing it on close.
        self.save_tb_file()
        self.status_label.setText(tr("status_external_keep_local", self.language))

    def _ensure_no_external_change_conflict(self):
        """Guard save/simulate operations against silent overwrite."""
        if self.external_change_pending:
            self.status_label.setText(tr("status_external_pending", self.language))
            self.external_change_bar.setVisible(True)
            return False
        ok = self.external_change_controller.ensure_no_conflict()
        if not ok:
            self.status_label.setText(tr("status_external_pending", self.language))
            self.external_change_bar.setVisible(True)
        return ok

    def _reset_problem_index(self):
        self.problems_controller.reset()

    def _append_problems_to_console(self, messages, folder_path):
        self.problems_controller.append_problems(messages, folder_path)

    def _handle_console_link(self, url):
        problem = self.problems_controller.resolve_link(url.toString())
        if not problem:
            return

        self._jump_to_problem(problem)

    def _jump_to_problem(self, problem):
        if not isinstance(problem, dict):
            return

        file_path = problem["file"]
        line = max(problem["line"] - 1, 0)
        col = max(problem["col"] - 1, 0)

        # Keep editing flow safe: jump directly only on current or selectable TB files.
        if file_path == self.current_tb_file:
            self.editor.setCursorPosition(line, col)
            self.editor.ensureLineVisible(line)
            self.editor.setFocus()
            return

        if file_path in self.available_tb_files:
            self._load_tb_file(file_path)
            self.project_selection_controller.select_tb_in_combo(file_path)
            self.editor.setCursorPosition(line, col)
            self.editor.ensureLineVisible(line)
            self.editor.setFocus()
            return

        self.problems_controller.append_jump_unavailable(file_path)

    def _refresh_project(self, preserve_tb=None):
        self.available_tb_files = self.project_load_controller.refresh_project(preserve_tb=preserve_tb)

    def refresh_recent_projects(self):
        self.project_selection_controller.refresh_recent_projects()

    def add_recent_project(self, folder_path):
        self.project_selection_controller.add_recent_project(folder_path)

    def open_recent_project(self, index):
        self.project_selection_controller.open_recent_project(index)

    def validate_project(self):
        self.simulation_flow_controller.validate_project()

    def run_simulation(self):
        self.simulation_flow_controller.run_simulation()

    @staticmethod
    def _primary_screen_geometry():
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.availableGeometry()

    def open_config_dialog(self):
        config_dialog = ConfigDialog(self)
        if config_dialog.exec():
            cfg = self.settings.get_config()
            self.language = normalize_lang(cfg.get("language", "en"))
            self.theme = cfg.get("theme", "dark")
            self.editor_font_size = self._sanitize_font_size(cfg.get("editor_font_size", 12))
            self.apply_theme()
            self._set_editor_font_size(self.editor_font_size, persist=False)
            self.apply_language()

    def maybe_check_updates_on_startup(self):
        self.update_controller.maybe_check_updates_on_startup(self)

    def maybe_setup_linux_desktop_entry(self):
        self.linux_desktop_controller.maybe_setup_linux_desktop_entry(self)

    def check_for_updates(self, silent_errors=False):
        self.update_controller.check_for_updates(self, silent_errors=silent_errors)

    def load_config(self):
        config = self.settings.get_config()
        folder_path = config.get("verilog_folder", "") if config else ""
        project_mode = config.get("project_mode", "auto") if config else "auto"
        selected_tb = config.get("selected_tb", "") if config else ""
        self.language = normalize_lang(config.get("language", "en")) if config else self.language
        self.theme = config.get("theme", "dark") if config else self.theme
        self.editor_font_size = self._sanitize_font_size(config.get("editor_font_size", 12)) if config else 12

        self.folder_entry.setText(folder_path)
        self.project_selection_controller.set_mode_value(project_mode)
        self._set_editor_font_size(self.editor_font_size, persist=False)
        self._refresh_project(preserve_tb=selected_tb)
        if folder_path and os.path.isdir(folder_path):
            self.project_selection_controller.add_recent_project(folder_path)

    def reload_verilog_folder(self):
        self._refresh_project(preserve_tb=self.current_tb_file)

    def tb_selection_changed(self):
        tb_path = self.project_selection_controller.selected_tb_path()
        if tb_path:
            self._load_tb_file(tb_path)

    def tb_changed(self):
        self.status_label.setText(tr("status_dirty", self.language))
        self.save_button.setEnabled(True)

    def save_tb_file(self):
        if not self.current_tb_file:
            return
        if not self._ensure_no_external_change_conflict():
            return

        target_file = self.current_tb_file
        backup_file = f"{target_file}.bak"
        temp_file = f"{target_file}.tmp"
        content = self.editor.text()
        # Recover files previously affected by CRLF double-conversion on Windows.
        while "\r\r\n" in content:
            content = content.replace("\r\r\n", "\r\n")

        # Keep a backup copy of the last saved version without removing the source file.
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as src:
                original_content = src.read()
            with open(backup_file, "w", encoding="utf-8", newline="") as bak:
                bak.write(original_content)

        # Atomic save to avoid partial writes or stale content on refresh.
        self.external_change_controller.begin_internal_save()
        try:
            with open(temp_file, "w", encoding="utf-8", newline="") as file:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_file, target_file)
        finally:
            self.external_change_controller.end_internal_save()

        self.external_change_controller.sync_after_save()
        self._hide_external_change_banner()

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
                "project_mode": self.project_selection_controller.current_mode(),
                "selected_tb": self.current_tb_file or "",
            }
        )
        self.project_selection_controller.add_recent_project(folder_selected)

    def closeEvent(self, event):
        """Close GTKWave process when the main window closes."""
        self.external_change_controller.close()
        self.simulator.close_gtkwave()
        event.accept()


def main():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BenchSim.BenchSim")
        except Exception:
            pass

    app = QApplication([])
    app.setApplicationName("benchsim")
    app.setApplicationDisplayName("BenchSim")
    app.setOrganizationName("BenchSim")
    if hasattr(app, "setDesktopFileName"):
        app.setDesktopFileName("benchsim")
    app.setWindowIcon(get_app_icon(get_resource_base_dir()))
    window = BenchSimApp()
    window.show()
    window.setWindowState(window.windowState() | Qt.WindowState.WindowMaximized)
    # Some Linux window managers ignore the first maximize request.
    QTimer.singleShot(0, window.showMaximized)
    QTimer.singleShot(120, window.showMaximized)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
