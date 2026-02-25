"""Controller for Linux desktop launcher setup in packaged builds."""

import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox


class LinuxDesktopController:
    """Manage .desktop launcher install/update prompts for Linux binaries."""

    def __init__(
        self,
        *,
        settings,
        base_dir,
        dispatcher,
        translate,
        language_getter,
    ):
        self.settings = settings
        self.base_dir = base_dir
        self.dispatcher = dispatcher
        self._tr = translate
        self.language_getter = language_getter

    def _install_linux_desktop_entry(self, exec_path):
        lang = self.language_getter()
        icon_src = self.base_dir / "benchsim.png"
        if not icon_src.is_file():
            return False, self._tr("desktop_setup_error_icon", lang)

        icon_dir = Path.home() / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps"
        app_dir = Path.home() / ".local" / "share" / "applications"
        icon_dir.mkdir(parents=True, exist_ok=True)
        app_dir.mkdir(parents=True, exist_ok=True)

        icon_dst = icon_dir / "benchsim.png"
        shutil.copy2(icon_src, icon_dst)

        desktop_path = app_dir / "benchsim.desktop"
        desktop_content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=BenchSim\n"
            "Comment=Testbench simulation runner for Icarus Verilog + GTKWave\n"
            f"Exec={exec_path}\n"
            f"Icon={icon_dst}\n"
            "Terminal=false\n"
            "Categories=Development;Electronics;\n"
            "StartupWMClass=benchsim\n"
            "X-GNOME-WMClass=benchsim\n"
        )
        desktop_path.write_text(desktop_content, encoding="utf-8")
        desktop_path.chmod(0o755)

        update_db = shutil.which("update-desktop-database")
        if update_db:
            subprocess.run([update_db, str(app_dir)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        update_icon_cache = shutil.which("gtk-update-icon-cache")
        if update_icon_cache:
            icon_root = Path.home() / ".local" / "share" / "icons" / "hicolor"
            subprocess.run(
                [update_icon_cache, "-f", "-t", str(icon_root)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return True, ""

    def maybe_setup_linux_desktop_entry(self, parent_widget):
        """Offer automatic desktop launcher setup on Linux packaged builds."""
        if not sys.platform.startswith("linux"):
            return
        if not getattr(sys, "frozen", False):
            return

        cfg = self.settings.get_config()
        desktop_path = Path.home() / ".local" / "share" / "applications" / "benchsim.desktop"
        current_exec = str(Path(sys.executable).resolve())
        installed = cfg.get("linux_desktop_installed", False)
        last_exec = cfg.get("linux_desktop_exec", "")
        dismissed = cfg.get("linux_desktop_prompt_dismissed", False)

        stale_desktop = False
        if desktop_path.is_file():
            try:
                desktop_text = desktop_path.read_text(encoding="utf-8")
                stale_desktop = ("Icon=benchsim" in desktop_text) or ("X-GNOME-WMClass=benchsim" not in desktop_text)
            except Exception:  # pylint: disable=broad-exception-caught
                stale_desktop = True

        needs_install = (not desktop_path.is_file()) or (not installed) or stale_desktop
        moved_exec = bool(installed and last_exec and last_exec != current_exec)
        if not needs_install and not moved_exec:
            return

        # If launcher is missing/stale, prompt again even if user dismissed before.
        if needs_install and dismissed and desktop_path.is_file() and not stale_desktop:
            return

        lang = self.language_getter()
        body_key = "desktop_setup_update_body" if moved_exec else "desktop_setup_first_body"
        answer = QMessageBox.question(
            parent_widget,
            self._tr("desktop_setup_title", lang),
            self._tr(body_key, lang, path=current_exec),
        )
        if answer != QMessageBox.StandardButton.Yes:
            if needs_install:
                self.settings.update_config({"linux_desktop_prompt_dismissed": True})
            return

        success, error_text = self._install_linux_desktop_entry(current_exec)
        if not success:
            QMessageBox.warning(
                parent_widget,
                self._tr("popup_warning_title", lang),
                self._tr("desktop_setup_error", lang, error=error_text),
            )
            return

        self.settings.update_config(
            {
                "linux_desktop_installed": True,
                "linux_desktop_exec": current_exec,
                "linux_desktop_prompt_dismissed": False,
            }
        )
        self.dispatcher.handle_message(
            {
                "type": "success",
                "message": self._tr("desktop_setup_done", lang),
                "extras": ["toast"],
            }
        )
