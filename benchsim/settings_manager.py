"""
Settings management for the application.
"""
import sys
import os
import json

class SettingsManager:
    """
    Manages application settings stored in a JSON configuration file.
    """
    def __init__(self, app_name, filename="config.json", legacy_app_names=None):
        self.app_name = app_name
        self.filename = filename
        self.config_file = self.get_config_path()
        self.legacy_app_names = legacy_app_names or []

    def get_config_path(self):
        """Return the absolute path to the configuration file."""
        if sys.platform.startswith("win"):
            base_dir = os.getenv("APPDATA")
        elif sys.platform.startswith("darwin"):
            base_dir = os.path.expanduser("~/Library/Application Support")
        else:  # Linux - Unix
            base_dir = os.path.expanduser("~/.config")

        config_dir = os.path.join(base_dir, self.app_name)
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, self.filename)

    def get_config(self):
        """Load and return the configuration dictionary."""
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)

        for legacy_name in self.legacy_app_names:
            legacy_file = self.get_config_path_for_app(legacy_name)
            if os.path.exists(legacy_file):
                with open(legacy_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        return {}

    def get_config_path_for_app(self, app_name):
        """Return config path for a specific app name."""
        if sys.platform.startswith("win"):
            base_dir = os.getenv("APPDATA")
        elif sys.platform.startswith("darwin"):
            base_dir = os.path.expanduser("~/Library/Application Support")
        else:
            base_dir = os.path.expanduser("~/.config")

        config_dir = os.path.join(base_dir, app_name)
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, self.filename)

    def update_config(self, updates):
        """Update specific keys in the configuration."""
        config = self.get_config()
        config.update(updates)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    
        # --- Helpers para listas de recientes ---
    def get_list(self, key):
        cfg = self.get_config()
        val = cfg.get(key, [])
        return val if isinstance(val, list) else []

    def save_list(self, key, values):
        cfg = self.get_config()
        cfg[key] = values
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)

    def push_recent(self, key, item, limit=10, normalize=True):
        """Inserta al frente, sin duplicados, con tamaño máximo."""
        if not item:
            return
        if normalize:
            try:
                item = os.path.abspath(os.path.expanduser(item))
            except Exception:
                pass
        items = [i for i in self.get_list(key) if i and i != item]
        items.insert(0, item)
        self.save_list(key, items[:limit])

    def clear_recent(self, key):
        self.save_list(key, [])

    def prune_missing_paths(self, key):
        """Elimina entradas que ya no existen en disco."""
        items = self.get_list(key)
        kept = [p for p in items if os.path.exists(p)]
        if kept != items:
            self.save_list(key, kept)
