"""Controller for atomic testbench save workflow."""

import os


class TBSaveController:
    """Persist editor content safely and keep external-change state in sync."""

    def __init__(
        self,
        *,
        editor,
        external_change_controller,
        hide_external_change_banner,
        set_save_button_enabled,
        set_status_text,
        translate,
        language_getter,
    ):
        self.editor = editor
        self.external_change_controller = external_change_controller
        self.hide_external_change_banner = hide_external_change_banner
        self.set_save_button_enabled = set_save_button_enabled
        self.set_status_text = set_status_text
        self._tr = translate
        self.language_getter = language_getter

    def save_tb_file(self, target_file):
        """Save current editor content to target file using atomic replace."""
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
        self.hide_external_change_banner()
        self.set_save_button_enabled(False)
        self.set_status_text(self._tr("status_saved", self.language_getter()))
        return True
