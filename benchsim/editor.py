"""Provides a Verilog editor widget using QScintilla with syntax highlighting and basic features."""

import json
from pathlib import Path

# pylint: disable=no-name-in-module
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.Qsci import QsciLexerVerilog, QsciScintilla


class VerilogEditor(QsciScintilla):
    """A QScintilla-based code editor configured for Verilog syntax."""

    file_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.is_loading = False
        self.base_dir = Path(__file__).resolve().parent

        self.lexer = QsciLexerVerilog()
        self.lexer.setFont(QFont("Consolas", 12))
        self.setLexer(self.lexer)

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

        self.apply_theme("dark")
        self.textChanged.connect(self.trigger_change)

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
