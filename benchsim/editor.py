"""Provides a Verilog editor widget using QScintilla with syntax highlighting and basic features."""

import json
import re
import sys
from pathlib import Path

# pylint: disable=no-name-in-module
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QGuiApplication
from PyQt6.Qsci import QsciAPIs, QsciLexerVerilog, QsciScintilla


class VerilogEditor(QsciScintilla):
    """A QScintilla-based code editor configured for Verilog syntax."""

    file_changed = pyqtSignal()
    zoom_requested = pyqtSignal(int)
    zoom_reset_requested = pyqtSignal()
    VERILOG_COMPLETIONS = {
        "always",
        "always_comb",
        "always_ff",
        "always_latch",
        "assign",
        "begin",
        "case",
        "casex",
        "casez",
        "default",
        "else",
        "end",
        "endcase",
        "endfunction",
        "endmodule",
        "endgenerate",
        "endtask",
        "for",
        "forever",
        "function",
        "generate",
        "if",
        "initial",
        "inout",
        "input",
        "logic",
        "localparam",
        "module",
        "negedge",
        "or",
        "output",
        "parameter",
        "posedge",
        "reg",
        "repeat",
        "task",
        "while",
        "wire",
        "$display",
        "$dumpfile",
        "$dumpvars",
        "$finish",
        "$monitor",
        "`define",
        "`ifdef",
        "`ifndef",
        "`endif",
    }
    MIN_FONT_SIZE = 8
    MAX_FONT_SIZE = 36

    def __init__(self, parent=None):
        super().__init__(parent)

        self.is_loading = False
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            self.base_dir = Path(sys._MEIPASS) / "benchsim"
        else:
            self.base_dir = Path(__file__).resolve().parent

        self.lexer = QsciLexerVerilog()
        self.font_family = "Consolas"
        self.font_size = 12
        self.lexer.setFont(QFont(self.font_family, self.font_size))
        self.setLexer(self.lexer)

        self.apis = QsciAPIs(self.lexer)
        self.dynamic_completions = set()
        self._refresh_api()

        self.setMarginWidth(0, "0000")
        self.setMarginLineNumbers(0, True)
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setCaretLineVisible(True)
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)

        self.setTabWidth(2)
        self.setIndentationWidth(2)
        self.setIndentationsUseTabs(False)
        self.setTabIndents(True)
        self.setBackspaceUnindents(True)
        self.setIndentationGuides(True)
        self.setAutoIndent(True)
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAPIs)
        self.setAutoCompletionThreshold(2)
        self.setAutoCompletionCaseSensitivity(False)
        self.set_editor_font_size(self.font_size)

        self.apply_theme("dark")
        self.textChanged.connect(self.trigger_change)
        self.completion_timer = QTimer(self)
        self.completion_timer.setSingleShot(True)
        self.completion_timer.setInterval(500)
        self.completion_timer.timeout.connect(self._refresh_dynamic_completions)

    def _load_theme_colors(self, theme_name):
        theme_file = self.base_dir / "themes" / f"editor_{theme_name}.json"
        fallback_file = self.base_dir / "themes" / "editor_dark.json"
        selected = theme_file if theme_file.is_file() else fallback_file

        with open(selected, "r", encoding="utf-8") as file:
            return json.load(file)

    def apply_theme(self, theme_name):
        """Apply editor palette using external theme files."""
        colors = self._load_theme_colors(theme_name)

        default_color = QColor(colors["default"])
        paper_color = QColor(colors["paper"])

        self.lexer.setPaper(paper_color)
        self.lexer.setDefaultPaper(paper_color)
        self.lexer.setDefaultColor(default_color)
        self.setColor(default_color)
        self.setPaper(paper_color)
        default_rgb = default_color.rgb() & 0xFFFFFF
        paper_rgb = paper_color.rgb() & 0xFFFFFF
        self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, QsciScintilla.STYLE_DEFAULT, default_rgb)
        self.SendScintilla(QsciScintilla.SCI_STYLESETBACK, QsciScintilla.STYLE_DEFAULT, paper_rgb)
        self.lexer.setColor(QColor(colors["keyword"]), QsciLexerVerilog.Keyword)
        self.lexer.setColor(QColor(colors["preproc"]), QsciLexerVerilog.Preprocessor)
        self.lexer.setColor(QColor(colors["comment"]), QsciLexerVerilog.Comment)
        self.lexer.setColor(QColor(colors["string"]), QsciLexerVerilog.String)
        self.lexer.setColor(QColor(colors["number"]), QsciLexerVerilog.Number)
        self.lexer.setColor(default_color, QsciLexerVerilog.Identifier)
        self.lexer.setColor(default_color, QsciLexerVerilog.Operator)
        self.lexer.setColor(QColor(colors["system_task"]), QsciLexerVerilog.SystemTask)
        self.lexer.setColor(QColor(colors["port_conn"]), QsciLexerVerilog.PortConnection)
        self.lexer.setColor(QColor(colors["port_conn"]), QsciLexerVerilog.DeclareInputPort)
        self.lexer.setColor(QColor(colors["port_conn"]), QsciLexerVerilog.DeclareOutputPort)
        self.lexer.setColor(QColor(colors["port_conn"]), QsciLexerVerilog.DeclareInputOutputPort)
        self.lexer.setColor(QColor(colors["keyword2"]), QsciLexerVerilog.KeywordSet2)
        self.lexer.setColor(QColor(colors["user_kw"]), QsciLexerVerilog.UserKeywordSet)
        self.setMarginsBackgroundColor(QColor(colors["margin_bg"]))
        self.setMarginsForegroundColor(QColor(colors["margin_fg"]))
        self.setCaretLineBackgroundColor(QColor(colors["caret_line"]))
        self.setCaretForegroundColor(QColor(colors["caret"]))
        self.setFoldMarginColors(QColor(colors["fold_bg"]), QColor(colors["fold_fg"]))

    def set_text_safely(self, text):
        """Set the editor text without triggering file_changed signal."""
        self.is_loading = True
        self.setText(text)
        self.is_loading = False

    def trigger_change(self):
        """Emit file_changed when content changes from user edits."""
        if not self.is_loading:
            self.file_changed.emit()
        self.completion_timer.start()

    @staticmethod
    def _extract_document_symbols(content):
        symbols = set()
        decl_pattern = re.compile(
            r"\b(input|output|inout|wire|reg|logic|parameter|localparam)\b([^;]*);",
            re.IGNORECASE | re.DOTALL,
        )
        id_pattern = re.compile(r"\b[_a-zA-Z][_a-zA-Z0-9]*\b")

        for match in decl_pattern.finditer(content):
            tail = re.sub(r"\[[^\]]+\]", " ", match.group(2))
            for name in id_pattern.findall(tail):
                lowered = name.lower()
                if lowered in {"signed", "unsigned", "reg", "wire", "logic"}:
                    continue
                symbols.add(name)

        for pattern in (r"\bmodule\s+([_a-zA-Z][_a-zA-Z0-9]*)", r"\btask\s+([_a-zA-Z][_a-zA-Z0-9]*)"):
            for mod_match in re.finditer(pattern, content):
                symbols.add(mod_match.group(1))
        return symbols

    def _refresh_api(self):
        self.apis = QsciAPIs(self.lexer)
        for token in sorted(self.VERILOG_COMPLETIONS.union(self.dynamic_completions)):
            self.apis.add(token)
        self.apis.prepare()
        self.lexer.setAPIs(self.apis)

    def _refresh_dynamic_completions(self):
        symbols = self._extract_document_symbols(self.text())
        if symbols == self.dynamic_completions:
            return
        self.dynamic_completions = symbols
        self._refresh_api()

    def trigger_autocomplete(self):
        """Open completion popup at current caret."""
        self.autoCompleteFromAPIs()

    def set_editor_font_size(self, size):
        """Set editor and lexer font size with safe bounds."""
        try:
            value = int(size)
        except (TypeError, ValueError):
            value = self.font_size
        value = max(self.MIN_FONT_SIZE, min(self.MAX_FONT_SIZE, value))

        self.font_size = value
        font = QFont(self.font_family, self.font_size)
        self.setFont(font)
        self.setMarginsFont(font)
        self.lexer.setFont(font)
        self.SendScintilla(QsciScintilla.SCI_SETZOOM, 0)
        self.recolor()

    def get_editor_font_size(self):
        """Return current editor font size."""
        return self.font_size

    @staticmethod
    def _wheel_zoom_step(event):
        """Return normalized zoom step from wheel/trackpad events."""
        angle_delta = event.angleDelta().y()
        if angle_delta > 0:
            return 1
        if angle_delta < 0:
            return -1

        pixel_delta = event.pixelDelta().y()
        if pixel_delta > 0:
            return 1
        if pixel_delta < 0:
            return -1
        return 0

    def wheelEvent(self, event):
        """Handle Ctrl+wheel as managed font zoom to keep settings in sync."""
        modifiers = event.modifiers() | QGuiApplication.keyboardModifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            step = self._wheel_zoom_step(event)
            if step:
                self.zoom_requested.emit(step)
                event.accept()
                return
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        """Handle Ctrl zoom shortcuts in-editor and keep settings synchronized."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            key = event.key()
            if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.zoom_requested.emit(1)
                event.accept()
                return
            if key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
                self.zoom_requested.emit(-1)
                event.accept()
                return
            if key == Qt.Key.Key_0:
                self.zoom_reset_requested.emit()
                event.accept()
                return
        super().keyPressEvent(event)

    def find_text(self, query, *, forward=True, case_sensitive=False, whole_word=False, wrap=True):
        """Find text from current caret position."""
        if not query:
            return False
        return self.findFirst(
            query,
            False,  # regular expression
            case_sensitive,
            whole_word,
            wrap,
            forward,
            -1,
            -1,
            True,
        )

    def replace_current(self, replacement):
        """Replace currently selected match."""
        if not self.hasSelectedText():
            return False
        self.replace(replacement)
        return True

    def replace_all(self, query, replacement, *, case_sensitive=False, whole_word=False):
        """Replace all matches in document and return count."""
        if not query:
            return 0

        self.beginUndoAction()
        try:
            count = 0
            self.setCursorPosition(0, 0)
            while self.findFirst(
                query,
                False,
                case_sensitive,
                whole_word,
                False,
                True,
                -1,
                -1,
                True,
            ):
                self.replace(replacement)
                count += 1
            return count
        finally:
            self.endUndoAction()
