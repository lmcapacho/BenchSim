"""Controller for loading and syncing active testbench file in editor."""

import os
from dataclasses import dataclass


@dataclass
class TBLoadResult:
    """State returned after loading or merging a testbench file."""

    loaded: bool
    merged: bool = False
    conflict_count: int = 0


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
        stimuli_persistence,
        merge_controller,
    ):
        self.editor = editor
        self.status_label = status_label
        self.save_button = save_button
        self.external_change_controller = external_change_controller
        self._hide_external_banner = on_hide_external_banner
        self.stimuli_persistence = stimuli_persistence
        self.merge_controller = merge_controller

    def load_tb_file(self, tb_path, *, status_saved_text, status_dirty_text, merge_external=False):
        """Load a TB file into editor and align UI state."""
        if not tb_path or not os.path.isfile(tb_path):
            return TBLoadResult(False)
        with open(tb_path, "r", encoding="utf-8") as verilog_file:
            content = verilog_file.read()

        merged = False
        if merge_external:
            merge_result = self.merge_controller.merge_external(
                tb_path,
                content,
                local_content=self.editor.text(),
            )
            if not merge_result.merged:
                return TBLoadResult(False, conflict_count=merge_result.conflict_count)
            merged = merge_result.content != content
            content = merge_result.content
        else:
            managed_scenario = os.path.basename(tb_path) == "scenario.vh"
            if managed_scenario:
                content, restored = content, False
            else:
                content, restored, _restored_count, _dropped_count = self.stimuli_persistence.restore_into_tb_text(tb_path, content)
                self.stimuli_persistence.initialize_from_tb_text(tb_path, content)
            merged = restored
            self.merge_controller.ensure_snapshot(tb_path, content)

        self.editor.set_text_safely(content)
        self.external_change_controller.set_current_tb_file(tb_path)
        self._hide_external_banner()
        self.status_label.setText(status_dirty_text if merged else status_saved_text)
        self.save_button.setEnabled(merged)
        return TBLoadResult(True, merged=merged)
