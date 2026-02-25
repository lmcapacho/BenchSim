"""Controller for project mode/TB selection and recent projects."""

import os


class ProjectSelectionController:
    """Encapsulates project selectors and recent-project behavior."""

    def __init__(
        self,
        *,
        settings,
        mode_combo,
        tb_combo,
        recent_combo,
        translate,
        open_project_folder,
        get_current_tb_path,
    ):
        self.settings = settings
        self.mode_combo = mode_combo
        self.tb_combo = tb_combo
        self.recent_combo = recent_combo
        self._tr = translate
        self._open_project_folder = open_project_folder
        self._get_current_tb_path = get_current_tb_path

    def set_mode_value(self, mode_value):
        for index in range(self.mode_combo.count()):
            if self.mode_combo.itemData(index) == mode_value:
                self.mode_combo.setCurrentIndex(index)
                return

    def current_mode(self):
        return self.mode_combo.currentData()

    def selected_tb_path(self):
        if self.tb_combo.currentIndex() < 0:
            return None
        return self.tb_combo.currentData()

    def select_tb_in_combo(self, tb_path):
        if not tb_path:
            return
        for index in range(self.tb_combo.count()):
            if self.tb_combo.itemData(index) == tb_path:
                self.tb_combo.setCurrentIndex(index)
                return

    def refresh_recent_projects(self):
        self.settings.prune_missing_paths("recent_projects")
        recent_items = self.settings.get_list("recent_projects")
        self.recent_combo.blockSignals(True)
        self.recent_combo.clear()
        self.recent_combo.addItem(self._tr("recent_projects_placeholder"), "")
        for path in recent_items:
            self.recent_combo.addItem(os.path.basename(path) or path, path)
        self.recent_combo.setCurrentIndex(0)
        self.recent_combo.blockSignals(False)

    def add_recent_project(self, folder_path):
        if not folder_path:
            return
        self.settings.push_recent("recent_projects", folder_path, limit=12, normalize=True)
        self.refresh_recent_projects()

    def open_recent_project(self, index):
        if index <= 0:
            return
        folder_path = self.recent_combo.itemData(index)
        if not folder_path or not os.path.isdir(folder_path):
            self.refresh_recent_projects()
            return

        self._open_project_folder(folder_path)
        self.settings.update_config(
            {
                "verilog_folder": folder_path,
                "project_mode": self.current_mode(),
                "selected_tb": self._get_current_tb_path() or "",
            }
        )
        self.add_recent_project(folder_path)
