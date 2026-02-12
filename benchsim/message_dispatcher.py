# pylint: disable=no-name-in-module
from PyQt6.QtWidgets import QMessageBox
from .i18n import normalize_lang, tr
from .messages import is_error, is_success, is_warning, is_log

try:
    from pyqttoast import Toast, ToastPreset
    HAS_PYQTTOAST = True
except ImportError:
    HAS_PYQTTOAST = False

class MessageDispatcher:
    def __init__(self, console_widget, parent_window=None, language="en", popup_on=None, toast_on=None):
        """Dispatcher con políticas de visualización por tipo de mensaje.

        popup_on / toast_on son dicts con claves: "error", "warning", "success", "log"
        y valores bool que indican si, por defecto, ese tipo debe abrir popup o toast.
        """
        self.console = console_widget
        self.parent = parent_window
        self.language = normalize_lang(language)
        self.popup_on = popup_on or {"error": True, "warning": False, "success": False, "log": False}
        self.toast_on = toast_on or {"error": False, "warning": True, "success": True, "log": False}

    def set_language(self, language):
        """Update active UI language for popup/toast labels."""
        self.language = normalize_lang(language)

    def handle_message(self, msg):
        """Process and dispatch a message."""
        text = msg.get("message", "")
        extras = msg.get("extras", [])

        # Determinar nivel
        level = "log"
        if is_error(msg):
            level = "error"
            self.console.append(f'<span style="color:red;"><b>{text}</b></span>')
        elif is_success(msg):
            level = "success"
            self.console.append(f'<span style="color:green;"><b>{text}</b></span>')
        elif is_warning(msg):
            level = "warning"
            self.console.append(f'<span style="color:orange;"><b>{text}</b></span>')
        elif is_log(msg):
            level = "log"
            self.console.append(text)

        # Políticas + overrides puntuales por extras
        want_toast = ("toast" in extras) or self.toast_on.get(level, False)
        want_popup = ("popup" in extras) or self.popup_on.get(level, False)

        if want_toast:
            self.show_toast(title=tr("app_name", self.language), message=text)

        if want_popup and self.parent:
            if level == "error":
                QMessageBox.critical(self.parent, tr("popup_error_title", self.language), text)
            elif level == "warning":
                QMessageBox.warning(self.parent, tr("popup_warning_title", self.language), text)
            else:
                QMessageBox.information(self.parent, tr("popup_info_title", self.language), text)

    def show_toast(self, title='', message='', duration=3000):
        if not HAS_PYQTTOAST:
            return
        toast = Toast(self.parent)
        toast.setDuration(duration)
        if title:
            toast.setTitle(title)
        if message:
            toast.setText(message)
        toast.applyPreset(ToastPreset.SUCCESS)
        toast.show()
