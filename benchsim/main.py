"""Main Qt application for Verilog simulation workflow."""
import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# pylint: disable=no-name-in-module
from PyQt6.QtGui import QColor, QGuiApplication, QIcon, QKeySequence, QPainter, QPen, QPixmap, QShortcut
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
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QStyle,
)

try:
    from .editor import VerilogEditor
    from .i18n import normalize_lang, tr
    from .message_dispatcher import MessageDispatcher
    from .settings_dialog import ConfigDialog
    from .settings_manager import SettingsManager
    from .simulation_manager import SimulationManager
    from .updater import check_for_updates as check_updates_remote, get_current_version
except ImportError:
    from benchsim.editor import VerilogEditor
    from benchsim.i18n import normalize_lang, tr
    from benchsim.message_dispatcher import MessageDispatcher
    from benchsim.settings_dialog import ConfigDialog
    from benchsim.settings_manager import SettingsManager
    from benchsim.simulation_manager import SimulationManager
    from benchsim.updater import check_for_updates as check_updates_remote, get_current_version

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


def get_tool_icon(widget, theme_name, fallback_icon):
    """Return icon and whether fallback icon was used."""
    icon = QIcon.fromTheme(theme_name)
    used_fallback = False
    if icon.isNull():
        icon = widget.style().standardIcon(fallback_icon)
        used_fallback = True
    return icon, used_fallback


class BenchSimApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.current_tb_file = None
        self.available_tb_files = []
        self.problem_index = {}
        self.base_dir = get_resource_base_dir()

        self.simulator = SimulationManager()
        self.settings = SettingsManager(APP_NAME)
        cfg = self.settings.get_config()
        self.language = normalize_lang(cfg.get("language", "en"))
        self.theme = cfg.get("theme", "dark")

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
        self.find_input.returnPressed.connect(self.find_next)

        self.replace_label = QLabel("")
        self.replace_input = QLineEdit()
        self.replace_input.returnPressed.connect(self.replace_current)

        self.case_checkbox = QCheckBox("")
        self.whole_word_checkbox = QCheckBox("")

        self.find_prev_button = QPushButton("")
        self.find_prev_button.clicked.connect(self.find_prev)
        self.find_next_button = QPushButton("")
        self.find_next_button.clicked.connect(self.find_next)
        self.replace_button = QPushButton("")
        self.replace_button.clicked.connect(self.replace_current)
        self.replace_all_button = QPushButton("")
        self.replace_all_button.clicked.connect(self.replace_all)
        self.close_search_button = QToolButton()
        self.close_search_button.setIcon(QIcon.fromTheme("window-close"))
        self.close_search_button.clicked.connect(self.hide_search_bar)

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

        layout.addSpacing(15)

        self.editor = VerilogEditor(self)
        layout.addWidget(self.editor, 4)

        self.console = QTextBrowser()
        self.console.setReadOnly(True)
        self.console.setOpenLinks(False)
        self.console.setOpenExternalLinks(False)
        self.console.anchorClicked.connect(self._handle_console_link)
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
        self.refresh_recent_projects()
        self.apply_theme()
        self.apply_language()
        self.setup_shortcuts()
        self.editor.file_changed.connect(self.tb_changed)
        QTimer.singleShot(1200, self.maybe_check_updates_on_startup)
        QTimer.singleShot(1600, self.maybe_setup_linux_desktop_entry)

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
        self.shortcut_find.activated.connect(self.show_find_bar)

        self.shortcut_replace = QShortcut(QKeySequence.StandardKey.Replace, self)
        self.shortcut_replace.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_replace.activated.connect(self.show_replace_bar)

        self.shortcut_find_next = QShortcut(QKeySequence("F3"), self)
        self.shortcut_find_next.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_find_next.activated.connect(self.find_next)

        self.shortcut_find_prev = QShortcut(QKeySequence("Shift+F3"), self)
        self.shortcut_find_prev.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_find_prev.activated.connect(self.find_prev)

        self.shortcut_hide_search = QShortcut(QKeySequence("Escape"), self)
        self.shortcut_hide_search.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_hide_search.activated.connect(self.hide_search_bar)

        self.shortcut_autocomplete = QShortcut(QKeySequence("Ctrl+Space"), self)
        self.shortcut_autocomplete.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_autocomplete.activated.connect(self.editor.trigger_autocomplete)

    def apply_theme(self):
        """Apply UI and editor theme from external files."""
        theme_file = self.base_dir / "themes" / f"{self.theme}.qss"
        if not theme_file.is_file():
            theme_file = self.base_dir / "themes" / "dark.qss"
            self.theme = "dark"
        self.setStyleSheet(self.load_stylesheet(theme_file))
        self._apply_toolbar_icons()
        self.editor.apply_theme(self.theme)

    def _apply_toolbar_icons(self):
        """Apply system icons and tweak contrast where needed."""
        tint_color = QColor("#E4E4E4")
        on_windows_dark = sys.platform.startswith("win") and self.theme == "dark"

        icon, fallback = get_tool_icon(self, "folder-open", QStyle.StandardPixmap.SP_DirOpenIcon)
        if on_windows_dark and fallback:
            icon = self._tint_icon(icon, tint_color)
        self.folder_button.setIcon(icon)

        icon, fallback = get_tool_icon(self, "view-refresh", QStyle.StandardPixmap.SP_BrowserReload)
        if on_windows_dark and fallback:
            icon = self._tint_icon(icon, tint_color)
        self.reload_button.setIcon(icon)

        icon, fallback = get_tool_icon(self, "dialog-ok-apply", QStyle.StandardPixmap.SP_DialogYesButton)
        if on_windows_dark and fallback:
            icon = self._tint_icon(icon, tint_color)
        self.validate_tool_button.setIcon(icon)

        icon, fallback = get_tool_icon(self, "settings", QStyle.StandardPixmap.SP_FileDialogDetailedView)
        if fallback:
            alt = QIcon.fromTheme("preferences-system")
            if not alt.isNull():
                icon = alt
                fallback = False
        if fallback:
            icon = self._build_gear_icon(QColor("#E4E4E4" if self.theme == "dark" else "#1F2937"))
        elif on_windows_dark:
            icon = self._tint_icon(icon, tint_color)
        self.config_button.setIcon(icon)

    @staticmethod
    def _build_gear_icon(color, size=18):
        """Draw a minimal gear fallback icon for settings."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color)
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(6, 6, 6, 6)
        for angle in range(0, 360, 45):
            painter.save()
            painter.translate(size / 2, size / 2)
            painter.rotate(angle)
            painter.drawLine(0, -8, 0, -6)
            painter.restore()
        painter.end()
        return QIcon(pixmap)

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

        self.find_label.setText(tr("editor_find_label", self.language))
        self.replace_label.setText(tr("editor_replace_label", self.language))
        self.find_input.setPlaceholderText(tr("editor_find_placeholder", self.language))
        self.replace_input.setPlaceholderText(tr("editor_replace_placeholder", self.language))
        self.case_checkbox.setText(tr("editor_case_sensitive", self.language))
        self.whole_word_checkbox.setText(tr("editor_whole_word", self.language))
        self.find_prev_button.setText(tr("editor_find_prev", self.language))
        self.find_next_button.setText(tr("editor_find_next", self.language))
        self.replace_button.setText(tr("editor_replace", self.language))
        self.replace_all_button.setText(tr("editor_replace_all", self.language))
        self.close_search_button.setToolTip(tr("editor_close_search", self.language))
        self.refresh_recent_projects()
        self.dispatcher.set_language(self.language)

    def show_find_bar(self):
        self.search_bar.show()
        self.replace_input.hide()
        self.replace_label.hide()
        self.replace_button.hide()
        self.replace_all_button.hide()
        if self.editor.hasSelectedText():
            selected = self.editor.selectedText().replace("\n", "")
            if selected:
                self.find_input.setText(selected)
        self.find_input.setFocus()
        self.find_input.selectAll()

    def show_replace_bar(self):
        self.search_bar.show()
        self.replace_input.show()
        self.replace_label.show()
        self.replace_button.show()
        self.replace_all_button.show()
        if self.editor.hasSelectedText():
            selected = self.editor.selectedText().replace("\n", "")
            if selected:
                self.find_input.setText(selected)
        self.find_input.setFocus()
        self.find_input.selectAll()

    def hide_search_bar(self):
        if self.search_bar.isVisible():
            self.search_bar.hide()
            self.editor.setFocus()

    def _find(self, forward=True):
        query = self.find_input.text()
        if not query:
            self.status_label.setText(tr("editor_find_empty", self.language))
            return False

        found = self.editor.find_text(
            query,
            forward=forward,
            case_sensitive=self.case_checkbox.isChecked(),
            whole_word=self.whole_word_checkbox.isChecked(),
            wrap=True,
        )
        if not found:
            self.status_label.setText(tr("editor_not_found", self.language, query=query))
        return found

    def find_next(self):
        self.show_find_bar()
        self._find(forward=True)

    def find_prev(self):
        self.show_find_bar()
        self._find(forward=False)

    def replace_current(self):
        self.show_replace_bar()
        query = self.find_input.text()
        if not query:
            self.status_label.setText(tr("editor_find_empty", self.language))
            return

        selected = self.editor.selectedText()
        case_sensitive = self.case_checkbox.isChecked()
        matches = selected == query if case_sensitive else selected.lower() == query.lower()
        if not matches:
            if not self._find(forward=True):
                return

        replaced = self.editor.replace_current(self.replace_input.text())
        if not replaced:
            self.status_label.setText(tr("editor_replace_none", self.language))
            return
        self.status_label.setText(tr("editor_replace_done", self.language))
        self.save_button.setEnabled(True)
        self.find_next()

    def replace_all(self):
        self.show_replace_bar()
        query = self.find_input.text()
        if not query:
            self.status_label.setText(tr("editor_find_empty", self.language))
            return
        count = self.editor.replace_all(
            query,
            self.replace_input.text(),
            case_sensitive=self.case_checkbox.isChecked(),
            whole_word=self.whole_word_checkbox.isChecked(),
        )
        self.status_label.setText(tr("editor_replace_all_done", self.language, count=count))
        if count > 0:
            self.save_button.setEnabled(True)

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

    def _reset_problem_index(self):
        self.problem_index = {}

    def _parse_problems_from_stderr(self, stderr_text, folder_path):
        if not stderr_text:
            return []

        problems = []
        pattern = re.compile(r"^(?P<file>[^:\n]+):(?P<line>\d+)(?::(?P<col>\d+))?:\s*(?P<msg>.+)$")
        for raw_line in stderr_text.splitlines():
            line = raw_line.strip()
            match = pattern.match(line)
            if not match:
                continue

            file_token = match.group("file").strip().strip("\"'`")
            line_number = int(match.group("line"))
            col_value = match.group("col")
            column_number = int(col_value) if col_value else 1
            message = match.group("msg").strip()

            file_path = Path(file_token)
            if not file_path.is_absolute():
                file_path = Path(folder_path) / file_path

            problems.append(
                {
                    "file": str(file_path.resolve()),
                    "line": line_number,
                    "col": column_number,
                    "message": message,
                }
            )
        return problems

    def _append_problems_to_console(self, messages, folder_path):
        all_problems = []
        for message in messages:
            data = message.get("data", {})
            stderr_text = data.get("stderr", "")
            if not stderr_text:
                continue
            all_problems.extend(self._parse_problems_from_stderr(stderr_text, folder_path))

        if not all_problems:
            return

        self.console.append(
            f"<b>{tr('problems_count', self.language, count=len(all_problems))}</b>"
        )
        for index, problem in enumerate(all_problems, start=1):
            token = f"p{index}"
            self.problem_index[token] = problem
            location = (
                f"{html.escape(os.path.basename(problem['file']))}:"
                f"{problem['line']}:{problem['col']}"
            )
            message = html.escape(problem["message"])
            self.console.append(f'<a href="problem://{token}">{location}</a>  {message}')

    def _handle_console_link(self, url):
        raw = url.toString()
        if not raw.startswith("problem://"):
            return
        token = raw.replace("problem://", "", 1)
        problem = self.problem_index.get(token)
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
            self._select_tb_in_combo(file_path)
            self.editor.setCursorPosition(line, col)
            self.editor.ensureLineVisible(line)
            self.editor.setFocus()
            return

        self.console.append(
            tr("problems_jump_unavailable", self.language, file=os.path.basename(file_path))
        )

    def _refresh_project(self, preserve_tb=None):
        self._reset_problem_index()
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

    def refresh_recent_projects(self):
        self.settings.prune_missing_paths("recent_projects")
        recent_items = self.settings.get_list("recent_projects")
        self.recent_combo.blockSignals(True)
        self.recent_combo.clear()
        self.recent_combo.addItem(tr("recent_projects_placeholder", self.language), "")
        for path in recent_items:
            self.recent_combo.addItem(os.path.basename(path) or path, path)
        self.recent_combo.setCurrentIndex(0)
        self.recent_combo.blockSignals(False)

    def add_recent_project(self, folder_path):
        if not folder_path:
            return
        self.settings.push_recent("recent_projects", folder_path, limit=12, normalize=True)
        self.refresh_recent_projects()

    def open_recent_project(self, index):
        if index <= 0:
            return
        folder_path = self.recent_combo.itemData(index)
        if not folder_path or not os.path.isdir(folder_path):
            self.refresh_recent_projects()
            return

        self.folder_entry.setText(folder_path)
        self._refresh_project()
        self.settings.update_config(
            {
                "verilog_folder": folder_path,
                "project_mode": self._current_mode(),
                "selected_tb": self.current_tb_file or "",
            }
        )
        self.add_recent_project(folder_path)

    def validate_project(self):
        folder_path = self.folder_entry.text().strip()
        self._reset_problem_index()
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
        self._reset_problem_index()
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
        self._append_problems_to_console(messages, folder_path)

        if success:
            self.settings.update_config(
                {
                    "verilog_folder": folder_path,
                    "project_mode": self._current_mode(),
                    "selected_tb": tb_path or "",
                }
            )
            self.add_recent_project(folder_path)

    def open_config_dialog(self):
        config_dialog = ConfigDialog(self)
        if config_dialog.exec():
            cfg = self.settings.get_config()
            self.language = normalize_lang(cfg.get("language", "en"))
            self.theme = cfg.get("theme", "dark")
            self.apply_theme()
            self.apply_language()

    def maybe_check_updates_on_startup(self):
        """Check for updates when enabled in settings."""
        cfg = self.settings.get_config()
        if not cfg.get("update_auto_check", True):
            return
        self.check_for_updates(silent_errors=True)

    def _install_linux_desktop_entry(self, exec_path):
        icon_src = self.base_dir / "benchsim.png"
        if not icon_src.is_file():
            return False, tr("desktop_setup_error_icon", self.language)

        icon_dir = Path.home() / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps"
        app_dir = Path.home() / ".local" / "share" / "applications"
        icon_dir.mkdir(parents=True, exist_ok=True)
        app_dir.mkdir(parents=True, exist_ok=True)

        icon_dst = icon_dir / "benchsim.png"
        shutil.copy2(icon_src, icon_dst)

        desktop_path = app_dir / "benchsim.desktop"
        desktop_content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=BenchSim\n"
            "Comment=Testbench simulation runner for Icarus Verilog + GTKWave\n"
            f"Exec={exec_path}\n"
            f"Icon={icon_dst}\n"
            "Terminal=false\n"
            "Categories=Development;Electronics;\n"
            "StartupWMClass=benchsim\n"
            "X-GNOME-WMClass=benchsim\n"
        )
        desktop_path.write_text(desktop_content, encoding="utf-8")
        desktop_path.chmod(0o755)

        update_db = shutil.which("update-desktop-database")
        if update_db:
            subprocess.run([update_db, str(app_dir)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        update_icon_cache = shutil.which("gtk-update-icon-cache")
        if update_icon_cache:
            icon_root = Path.home() / ".local" / "share" / "icons" / "hicolor"
            subprocess.run(
                [update_icon_cache, "-f", "-t", str(icon_root)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        return True, ""

    def maybe_setup_linux_desktop_entry(self):
        """Offer automatic desktop launcher setup on Linux packaged builds."""
        if not sys.platform.startswith("linux"):
            return
        if not getattr(sys, "frozen", False):
            return

        cfg = self.settings.get_config()
        desktop_path = Path.home() / ".local" / "share" / "applications" / "benchsim.desktop"
        current_exec = str(Path(sys.executable).resolve())
        installed = cfg.get("linux_desktop_installed", False)
        last_exec = cfg.get("linux_desktop_exec", "")
        dismissed = cfg.get("linux_desktop_prompt_dismissed", False)

        stale_desktop = False
        if desktop_path.is_file():
            try:
                desktop_text = desktop_path.read_text(encoding="utf-8")
                stale_desktop = ("Icon=benchsim" in desktop_text) or ("X-GNOME-WMClass=benchsim" not in desktop_text)
            except Exception:  # pylint: disable=broad-exception-caught
                stale_desktop = True

        needs_install = (not desktop_path.is_file()) or (not installed) or stale_desktop
        moved_exec = bool(installed and last_exec and last_exec != current_exec)
        if not needs_install and not moved_exec:
            return

        # If launcher is missing/stale, prompt again even if user dismissed before.
        if needs_install and dismissed and desktop_path.is_file() and not stale_desktop:
            return

        body_key = "desktop_setup_update_body" if moved_exec else "desktop_setup_first_body"
        answer = QMessageBox.question(
            self,
            tr("desktop_setup_title", self.language),
            tr(body_key, self.language, path=current_exec),
        )
        if answer != QMessageBox.StandardButton.Yes:
            if needs_install:
                self.settings.update_config({"linux_desktop_prompt_dismissed": True})
            return

        success, error_text = self._install_linux_desktop_entry(current_exec)
        if not success:
            QMessageBox.warning(
                self,
                tr("popup_warning_title", self.language),
                tr("desktop_setup_error", self.language, error=error_text),
            )
            return

        self.settings.update_config(
            {
                "linux_desktop_installed": True,
                "linux_desktop_exec": current_exec,
                "linux_desktop_prompt_dismissed": False,
            }
        )
        self.dispatcher.handle_message(
            {
                "type": "success",
                "message": tr("desktop_setup_done", self.language),
                "extras": ["toast"],
            }
        )

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
        self.theme = config.get("theme", "dark") if config else self.theme

        self.folder_entry.setText(folder_path)
        self._set_mode_value(project_mode)
        self._refresh_project(preserve_tb=selected_tb)
        if folder_path and os.path.isdir(folder_path):
            self.add_recent_project(folder_path)

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
        self.add_recent_project(folder_selected)

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
