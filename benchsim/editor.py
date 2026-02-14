"""Provides a Verilog editor widget using QScintilla with syntax highlighting and basic features."""

import json
import re
import sys
from pathlib import Path

# pylint: disable=no-name-in-module
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.Qsci import QsciAPIs, QsciLexerVerilog, QsciScintilla


class VerilogEditor(QsciScintilla):
    """A QScintilla-based code editor configured for Verilog syntax."""

    file_changed = pyqtSignal()
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

    def __init__(self, parent=None):
        super().__init__(parent)

        self.is_loading = False
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            self.base_dir = Path(sys._MEIPASS) / "benchsim"
        else:
            self.base_dir = Path(__file__).resolve().parent

        self.lexer = QsciLexerVerilog()
        self.lexer.setFont(QFont("Consolas", 12))
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

        self.lexer.setPaper(QColor(colors["paper"]))
        self.lexer.setDefaultColor(QColor(colors["default"]))
        self.lexer.setColor(QColor(colors["keyword"]), QsciLexerVerilog.Keyword)
        self.lexer.setColor(QColor(colors["preproc"]), QsciLexerVerilog.Preprocessor)
        self.lexer.setColor(QColor(colors["comment"]), QsciLexerVerilog.Comment)
        self.lexer.setColor(QColor(colors["string"]), QsciLexerVerilog.String)
        self.lexer.setColor(QColor(colors["number"]), QsciLexerVerilog.Number)
        self.lexer.setColor(QColor(colors["system_task"]), QsciLexerVerilog.SystemTask)
        self.lexer.setColor(QColor(colors["port_conn"]), QsciLexerVerilog.PortConnection)
        self.lexer.setColor(QColor(colors["keyword2"]), QsciLexerVerilog.KeywordSet2)
        self.lexer.setColor(QColor(colors["user_kw"]), QsciLexerVerilog.UserKeywordSet)

        base_color = QColor(colors["paper"]).rgb() & 0xFFFFFF
        self.SendScintilla(QsciScintilla.SCI_STYLESETBACK, QsciScintilla.STYLE_DEFAULT, base_color)
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
