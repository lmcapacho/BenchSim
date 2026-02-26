"""Controller for settings dialog open/apply flow."""


class ConfigDialogController:
    """Open settings dialog and apply updated runtime UI state."""

    def __init__(
        self,
        *,
        settings,
        dialog_class,
        normalize_language,
        sanitize_font_size,
        set_runtime_state,
        apply_theme,
        set_editor_font_size,
        apply_language,
    ):
        self.settings = settings
        self.dialog_class = dialog_class
        self.normalize_language = normalize_language
        self.sanitize_font_size = sanitize_font_size
        self.set_runtime_state = set_runtime_state
        self.apply_theme = apply_theme
        self.set_editor_font_size = set_editor_font_size
        self.apply_language = apply_language

    def open_config_dialog(self, parent_widget):
        """Show config dialog and apply persisted values when accepted."""
        config_dialog = self.dialog_class(parent_widget)
        if not config_dialog.exec():
            return

        cfg = self.settings.get_config()
        language = self.normalize_language(cfg.get("language", "en"))
        theme = cfg.get("theme", "dark")
        editor_font_size = self.sanitize_font_size(cfg.get("editor_font_size", 12))
        self.set_runtime_state(language, theme, editor_font_size)
        self.apply_theme()
        self.set_editor_font_size(editor_font_size, persist=False)
        self.apply_language()
