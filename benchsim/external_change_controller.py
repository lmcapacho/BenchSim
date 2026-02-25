"""External testbench change tracking and conflict state."""

import os

# pylint: disable=no-name-in-module
from PyQt6.QtCore import QFileSystemWatcher, QObject, QTimer, pyqtSignal


class ExternalTBChangeController(QObject):
    """Track external file changes and expose conflict state."""

    pending_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_tb_file = None
        self.tb_disk_signature = None
        self._internal_save = False
        self._pending_conflict = False
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)

    @staticmethod
    def _file_signature(file_path):
        try:
            stat = os.stat(file_path)
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return None

    def _set_pending_conflict(self, pending):
        pending = bool(pending)
        if pending == self._pending_conflict:
            return
        self._pending_conflict = pending
        self.pending_changed.emit(self._pending_conflict)

    def _refresh_watch(self):
        watched = self._watcher.files()
        if watched:
            self._watcher.removePaths(watched)
        if self.current_tb_file and os.path.isfile(self.current_tb_file):
            self._watcher.addPath(self.current_tb_file)

    def _detect_external_change(self):
        if not self.current_tb_file:
            return False
        disk_sig = self._file_signature(self.current_tb_file)
        if disk_sig is None:
            return False
        if self.tb_disk_signature is None:
            self.tb_disk_signature = disk_sig
            return False
        return disk_sig != self.tb_disk_signature

    def set_current_tb_file(self, tb_path):
        self.current_tb_file = tb_path if tb_path and os.path.isfile(tb_path) else None
        self.tb_disk_signature = self._file_signature(self.current_tb_file) if self.current_tb_file else None
        self._set_pending_conflict(False)
        self._refresh_watch()

    def clear_current_tb_file(self):
        self.current_tb_file = None
        self.tb_disk_signature = None
        self._set_pending_conflict(False)
        self._refresh_watch()

    def keep_local_version(self):
        if not self.current_tb_file:
            return
        self.tb_disk_signature = self._file_signature(self.current_tb_file)
        self._set_pending_conflict(False)

    def begin_internal_save(self):
        self._internal_save = True

    def end_internal_save(self):
        self._internal_save = False
        self._refresh_watch()

    def sync_after_save(self):
        self.tb_disk_signature = self._file_signature(self.current_tb_file) if self.current_tb_file else None
        self._set_pending_conflict(False)
        self._refresh_watch()

    def ensure_no_conflict(self):
        if self._pending_conflict:
            return False
        if self._detect_external_change():
            self._set_pending_conflict(True)
            return False
        return True

    def close(self):
        watched = self._watcher.files()
        if watched:
            self._watcher.removePaths(watched)

    def _on_file_changed(self, changed_path):
        if self._internal_save:
            QTimer.singleShot(0, self._refresh_watch)
            return
        if not self.current_tb_file:
            return
        if os.path.normcase(changed_path) != os.path.normcase(self.current_tb_file):
            return
        if self._detect_external_change():
            self._set_pending_conflict(True)
        QTimer.singleShot(0, self._refresh_watch)
