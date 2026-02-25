"""Controller for loading and syncing active testbench file in editor."""

import os


class TBFileController:
    """Handle testbench file loading and editor-state synchronization."""

    def __init__(
        self,
        *,
        editor,
        status_label,
        save_button,
        external_change_controller,
        on_hide_external_banner,
    ):
        self.editor = editor
        self.status_label = status_label
        self.save_button = save_button
        self.external_change_controller = external_change_controller
        self._hide_external_banner = on_hide_external_banner

    def load_tb_file(self, tb_path, *, status_saved_text):
        """Load a TB file into editor and align UI state."""
        if not tb_path or not os.path.isfile(tb_path):
            return False
        with open(tb_path, "r", encoding="utf-8") as verilog_file:
            self.editor.set_text_safely(verilog_file.read())
        self.external_change_controller.set_current_tb_file(tb_path)
        self._hide_external_banner()
        self.status_label.setText(status_saved_text)
        self.save_button.setEnabled(False)
        return True
