"""Provides a QThread-based class to run subprocess commands 
asynchronously and emit their outputs."""
import subprocess

# pylint: disable=no-name-in-module
from PyQt6.QtCore import QThread, pyqtSignal

class ProcessRunner(QThread):
    """A thread class to execute a system command asynchronously.

    Captures both stdout and stderr outputs line by line,
    and emits them via PyQt signals.
    """
    output_line = pyqtSignal(str)
    error_line = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def __init__(self, command, cwd=None):
        """Initialize the ProcessRunner with the command and optional working directory."""
        super().__init__()
        self.command = command
        self.cwd = cwd
        self.process = None
        self.is_running = False

    def run(self):
        """Start the subprocess, capture its output and errors, and emit signals for each line."""
        self.is_running = True
        self.process = subprocess.Popen(
            self.command,
            shell=True,
            cwd=self.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        for line in self.process.stdout:
            self.output_line.emit(line.strip())

        for line in self.process.stderr:
            self.error_line.emit(line.strip())

        self.process.wait()
        self.is_running = False
        self.finished_signal.emit(self.process.returncode)

    def is_alive(self):
        """Check if the subprocess is currently running."""
        return self.is_running
