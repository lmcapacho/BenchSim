"""Provides a Verilog editor widget using QScintilla with syntax highlighting and basic features."""

# pylint: disable=no-name-in-module
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import pyqtSignal
from PyQt6.Qsci import QsciScintilla, QsciLexerVerilog

class VerilogEditor(QsciScintilla):
    """A QScintilla-based code editor configured for Verilog syntax.

    Provides syntax highlighting, auto-indentation, line numbers,
    and emits a signal when the file content changes.
    """
    file_changed = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize the Verilog editor with syntax highlighting, 
        margins, and indentation settings."""
        super().__init__(parent)

        self.is_loading = False

        lexer = QsciLexerVerilog()

        lexer.setPaper(QColor("#1E1E1E"))
        lexer.setFont(QFont("Consolas", 12))
        lexer.setDefaultColor(QColor("#D4D4D4"))

        lexer.setColor(QColor("#569CD6"), QsciLexerVerilog.Keyword)
        lexer.setColor(QColor("#D7BA7D"), QsciLexerVerilog.Preprocessor)
        lexer.setColor(QColor("#6A9955"), QsciLexerVerilog.Comment)
        lexer.setColor(QColor("#CE9178"), QsciLexerVerilog.String)
        lexer.setColor(QColor("#B5CEA8"), QsciLexerVerilog.Number)
        lexer.setColor(QColor("#C586C0"), QsciLexerVerilog.SystemTask)
        lexer.setColor(QColor("#4EC9B0"), QsciLexerVerilog.PortConnection)
        lexer.setColor(QColor("#9CDCFE"), QsciLexerVerilog.KeywordSet2)
        lexer.setColor(QColor("#D7BA7D"), QsciLexerVerilog.UserKeywordSet)

        self.setLexer(lexer)

        color = QColor("#1E1E1E").rgb() & 0xFFFFFF
        self.SendScintilla(QsciScintilla.SCI_STYLESETBACK, QsciScintilla.STYLE_DEFAULT, color)

        self.setMarginsBackgroundColor(QColor("#2D2D30"))
        self.setMarginsForegroundColor(QColor("#CCCCCC"))
        self.setMarginWidth(0, "0000")
        self.setMarginLineNumbers(0, True)

        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)

        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#2C313C"))
        self.setCaretForegroundColor(QColor("#FFFFFF"))

        # Folding settings
        self.setFoldMarginColors(QColor("#1E1E1E"), QColor("#2D2D30"))
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)

        self.setTabWidth(2)
        self.setIndentationWidth(2)
        self.setIndentationsUseTabs(False)
        self.setTabIndents(True)
        self.setBackspaceUnindents(True)
        self.setIndentationGuides(True)
        self.setAutoIndent(True)

        self.textChanged.connect(self.trigger_change)

    def set_text_safely(self, text):
        """Set the editor text without triggering the file_changed signal."""
        self.is_loading = True
        self.setText(text)
        self.is_loading = False

    def trigger_change(self):
        """Emit the file_changed signal when the text changes, 
        unless loading programmatically."""
        if not self.is_loading:
            self.file_changed.emit()
