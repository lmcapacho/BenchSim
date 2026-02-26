"""Controller for loading and persisting active project state."""

import os


class ProjectStateController:
    """Handle startup state hydration and folder-selection persistence."""

    def __init__(
        self,
        *,
        settings,
        normalize_language,
        sanitize_font_size,
        folder_path_getter,
        current_mode_getter,
        current_tb_getter,
        set_runtime_state,
        set_folder_text,
        set_mode_value,
        set_editor_font_size,
        refresh_project,
        add_recent_project,
    ):
        self.settings = settings
        self.normalize_language = normalize_language
        self.sanitize_font_size = sanitize_font_size
        self.folder_path_getter = folder_path_getter
        self.current_mode_getter = current_mode_getter
        self.current_tb_getter = current_tb_getter
        self.set_runtime_state = set_runtime_state
        self.set_folder_text = set_folder_text
        self.set_mode_value = set_mode_value
        self.set_editor_font_size = set_editor_font_size
        self.refresh_project = refresh_project
        self.add_recent_project = add_recent_project

    def load_config(self, default_language, default_theme, default_font_size):
        """Load config and apply initial UI state."""
        config = self.settings.get_config() or {}
        folder_path = config.get("verilog_folder", "")
        project_mode = config.get("project_mode", "auto")
        selected_tb = config.get("selected_tb", "")
        language = self.normalize_language(config.get("language", default_language))
        theme = config.get("theme", default_theme)
        editor_font_size = self.sanitize_font_size(config.get("editor_font_size", default_font_size))

        self.set_runtime_state(language, theme, editor_font_size)
        self.set_folder_text(folder_path)
        self.set_mode_value(project_mode)
        self.set_editor_font_size(editor_font_size, persist=False)
        self.refresh_project(preserve_tb=selected_tb)
        if folder_path and os.path.isdir(folder_path):
            self.add_recent_project(folder_path)

    def persist_selected_folder(self, folder_selected):
        """Persist folder context and update recents."""
        self.set_folder_text(folder_selected)
        self.refresh_project()
        self.settings.update_config(
            {
                "verilog_folder": folder_selected,
                "project_mode": self.current_mode_getter(),
                "selected_tb": self.current_tb_getter() or "",
            }
        )
        self.add_recent_project(folder_selected)

    def current_folder_or_home(self):
        """Return current folder field content or home as fallback."""
        return self.folder_path_getter() or os.path.expanduser("~")
