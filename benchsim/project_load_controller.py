"""Controller for project file discovery and TB list loading."""

import os


class ProjectLoadController:
    """Handle project refresh workflow: discovery, TB combo population, and default load."""

    def __init__(
        self,
        *,
        simulator,
        tb_combo,
        folder_path_getter,
        mode_getter,
        reset_problem_index,
        clear_editor,
        clear_external_change_state,
        load_tb_file,
        select_tb_in_combo,
        append_console,
        translate,
        language_getter,
    ):
        self.simulator = simulator
        self.tb_combo = tb_combo
        self.folder_path_getter = folder_path_getter
        self.mode_getter = mode_getter
        self.reset_problem_index = reset_problem_index
        self.clear_editor = clear_editor
        self.clear_external_change_state = clear_external_change_state
        self.load_tb_file = load_tb_file
        self.select_tb_in_combo = select_tb_in_combo
        self.append_console = append_console
        self._tr = translate
        self.language_getter = language_getter
        self.available_tb_files = []

    def refresh_project(self, preserve_tb=None):
        self.reset_problem_index()
        folder_path = self.folder_path_getter().strip()
        if not folder_path or not os.path.isdir(folder_path):
            self.available_tb_files = []
            self.tb_combo.clear()
            self.clear_external_change_state()
            self.clear_editor()
            return self.available_tb_files

        discovery = self.simulator.discover_project_files(folder_path, mode=self.mode_getter())
        self.available_tb_files = discovery["tb_files"]

        self.tb_combo.blockSignals(True)
        self.tb_combo.clear()
        for tb_file in self.available_tb_files:
            self.tb_combo.addItem(os.path.basename(tb_file), tb_file)
        self.tb_combo.blockSignals(False)

        selected_tb = preserve_tb if preserve_tb in self.available_tb_files else discovery["preferred_tb"]
        if selected_tb:
            self.select_tb_in_combo(selected_tb)
            self.load_tb_file(selected_tb)

        lang = self.language_getter()
        self.append_console(
            self._tr(
                "project_loaded",
                lang,
                mode=discovery["effective_mode"],
                tb_count=len(self.available_tb_files),
                source_count=len(discovery["source_files"]),
            )
        )
        return self.available_tb_files
