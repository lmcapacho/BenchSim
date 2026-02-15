"""Basic i18n support for BenchSim UI and runtime messages."""

DEFAULT_LANG = "en"

LANG_OPTIONS = {
    "en": "English",
    "es": "Español",
}

TRANSLATIONS = {
    "en": {
        "app_name": "BenchSim",
        "status_clean": "No unsaved changes",
        "status_dirty": "Unsaved changes",
        "status_saved": "Changes saved",
        "btn_save": "Save",
        "btn_simulate": "Simulate",
        "btn_validate": "Validate",
        "tooltip_save": "Save changes (Ctrl+S)",
        "tooltip_simulate": "Auto-save and run simulation (Ctrl+R)",
        "tooltip_validate": "Validate project and show compile files",
        "placeholder_folder": "Select project root folder...",
        "mode_auto": "Auto",
        "mode_icestudio": "Icestudio",
        "mode_generic": "Generic",
        "tooltip_mode": "Source discovery mode",
        "tooltip_tb": "Testbench to edit and simulate",
        "tooltip_recent_projects": "Open recently used project folder",
        "recent_projects_placeholder": "Recent projects...",
        "tooltip_select_folder": "Select folder",
        "tooltip_reload": "Reload project files",
        "tooltip_settings": "Simulator settings",
        "dialog_select_folder": "Select a folder",
        "settings_button": "Settings",
        "editor_find_label": "Find:",
        "editor_replace_label": "Replace:",
        "editor_find_placeholder": "Search text",
        "editor_replace_placeholder": "Replacement text",
        "editor_case_sensitive": "Case",
        "editor_whole_word": "Whole word",
        "editor_find_prev": "Prev",
        "editor_find_next": "Next",
        "editor_replace": "Replace",
        "editor_replace_all": "Replace All",
        "editor_close_search": "Close search bar",
        "editor_find_empty": "Enter text to search.",
        "editor_not_found": "No matches found for: {query}",
        "editor_replace_none": "No selected match to replace.",
        "editor_replace_done": "1 match replaced.",
        "editor_replace_all_done": "Replaced {count} matches.",
        "problems_title": "Problems",
        "problems_empty": "No problems detected.",
        "problems_count": "Problems found: {count}",
        "problems_jump_unavailable": "Cannot jump to this file in the editor: {file}",
        "project_loaded": "<b>Project loaded</b>: mode={mode}, tb={tb_count}, sources={source_count}",
        "validation_preview_title": "<b>Validation and compile preview</b>",
        "validation_preview_meta": "mode={mode}<br/>tb={tb}<br/>files={count}<br/><br/>",
        "validation_success": "Project is valid. mode={mode} tb={tb} sources={count}",
        "error_no_screen": "Unable to determine screen size for GTKWave.",
        "config_title": "Configure Tool Paths",
        "config_iverilog": "Icarus Verilog (iverilog) Path",
        "config_gtkwave": "GTKWave Path",
        "config_language": "Language",
        "config_theme": "Theme",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "config_save": "Save",
        "config_saved_title": "Settings Saved",
        "config_saved_body": "Configuration saved successfully.",
        "config_select_exec": "Select {program}",
        "config_executables": "Executables",
        "config_all_files": "All Files",
        "config_update_auto": "Check updates at startup",
        "config_update_prerelease": "Include pre-releases (RC)",
        "config_check_updates_now": "Check updates now",
        "desktop_setup_title": "Desktop launcher",
        "desktop_setup_first_body": (
            "Create a BenchSim launcher in your applications menu?\n\n"
            "Executable:\n{path}"
        ),
        "desktop_setup_update_body": (
            "BenchSim executable path changed.\n"
            "Update launcher to the new path?\n\n"
            "Executable:\n{path}"
        ),
        "desktop_setup_done": "Desktop launcher installed.",
        "desktop_setup_error": "Could not install desktop launcher: {error}",
        "desktop_setup_error_icon": "Application icon file was not found.",
        "popup_error_title": "Error",
        "popup_warning_title": "Warning",
        "popup_info_title": "Information",
        "msg_folder_invalid": "Project folder is not set or does not exist.",
        "msg_iverilog_invalid": "Icarus Verilog path is invalid.",
        "msg_gtkwave_invalid": "GTKWave path is invalid.",
        "msg_no_sources": "No .v source files found to compile.",
        "msg_no_compile_files": "No source files available to compile in selected project.",
        "msg_multiple_icestudio": (
            "Multiple subprojects detected in ice-build. "
            "Open a single project folder, for example: ice-build/<project_name>/"
        ),
        "msg_compile_error": "<b>Compilation error:</b><br/><pre>{stderr}</pre>",
        "msg_sim_error": "<b>Simulation error:</b><br/><pre>{stderr}</pre>",
        "msg_no_vcd": "Simulation finished but no .vcd file was found.",
        "msg_gtkw_config_error": "Could not generate GTKWave configuration.",
        "msg_compiling": "<b>Compiling...</b><br/>files={count} mode={mode}<br/>",
        "msg_running": "<b>Running simulation...</b><br/>",
        "msg_opening_gtkw": "<b>Opening GTKWave...</b><br/>{cmd}<br/>",
        "msg_gtkw_running": "<b>GTKWave is already running.</b><br/>VCD: {vcd}<br/>",
        "msg_sim_updated": "Simulation updated",
        "msg_gtkw_restarting": "<b>Reloading GTKWave with updated simulation...</b><br/>",
        "msg_gtkw_closing": "<b>Closing GTKWave...</b><br/>",
        "msg_gtkw_closed": "<b>GTKWave closed.</b><br/>",
        "msg_gtkw_close_error": "<pre style='color:#E57373'>Error closing GTKWave: {error}</pre>",
        "update_check_failed": "Could not check for updates: {error}",
        "update_not_available": "BenchSim is up to date ({version}).",
        "update_available_title": "Update available",
        "update_available_body": (
            "Current version: {current}\n"
            "Latest version: {latest}\n\n"
            "Open release page to download and install?"
        ),
    },
    "es": {
        "app_name": "BenchSim",
        "status_clean": "Sin cambios",
        "status_dirty": "Cambios sin guardar",
        "status_saved": "Cambios guardados",
        "btn_save": "Guardar",
        "btn_simulate": "Simular",
        "btn_validate": "Validar",
        "tooltip_save": "Guardar cambios (Ctrl+S)",
        "tooltip_simulate": "Guardar automáticamente y ejecutar simulación (Ctrl+R)",
        "tooltip_validate": "Validar proyecto y mostrar archivos de compilación",
        "placeholder_folder": "Selecciona la carpeta raíz del proyecto...",
        "mode_auto": "Auto",
        "mode_icestudio": "Icestudio",
        "mode_generic": "Genérico",
        "tooltip_mode": "Modo de detección de archivos fuente",
        "tooltip_tb": "Testbench a editar y simular",
        "tooltip_recent_projects": "Abrir carpeta de proyecto reciente",
        "recent_projects_placeholder": "Proyectos recientes...",
        "tooltip_select_folder": "Seleccionar carpeta",
        "tooltip_reload": "Recargar archivos del proyecto",
        "tooltip_settings": "Configuración del simulador",
        "dialog_select_folder": "Selecciona una carpeta",
        "settings_button": "Config",
        "editor_find_label": "Buscar:",
        "editor_replace_label": "Reemplazar:",
        "editor_find_placeholder": "Texto a buscar",
        "editor_replace_placeholder": "Texto de reemplazo",
        "editor_case_sensitive": "Mayúsc/minúsc",
        "editor_whole_word": "Palabra completa",
        "editor_find_prev": "Anterior",
        "editor_find_next": "Siguiente",
        "editor_replace": "Reemplazar",
        "editor_replace_all": "Reemplazar todo",
        "editor_close_search": "Cerrar barra de búsqueda",
        "editor_find_empty": "Escribe texto para buscar.",
        "editor_not_found": "No se encontraron coincidencias para: {query}",
        "editor_replace_none": "No hay coincidencia seleccionada para reemplazar.",
        "editor_replace_done": "1 coincidencia reemplazada.",
        "editor_replace_all_done": "Se reemplazaron {count} coincidencias.",
        "problems_title": "Problemas",
        "problems_empty": "No se detectaron problemas.",
        "problems_count": "Problemas encontrados: {count}",
        "problems_jump_unavailable": "No se puede saltar a este archivo en el editor: {file}",
        "project_loaded": "<b>Proyecto cargado</b>: modo={mode}, tb={tb_count}, fuentes={source_count}",
        "validation_preview_title": "<b>Validación y vista previa de compilación</b>",
        "validation_preview_meta": "modo={mode}<br/>tb={tb}<br/>archivos={count}<br/><br/>",
        "validation_success": "Proyecto válido. modo={mode} tb={tb} fuentes={count}",
        "error_no_screen": "No se pudo determinar el tamaño de pantalla para GTKWave.",
        "config_title": "Configurar rutas de herramientas",
        "config_iverilog": "Ruta de Icarus Verilog (iverilog)",
        "config_gtkwave": "Ruta de GTKWave",
        "config_language": "Idioma",
        "config_theme": "Tema",
        "theme_dark": "Oscuro",
        "theme_light": "Claro",
        "config_save": "Guardar",
        "config_saved_title": "Configuración guardada",
        "config_saved_body": "La configuración se guardó correctamente.",
        "config_select_exec": "Seleccionar {program}",
        "config_executables": "Ejecutables",
        "config_all_files": "Todos los archivos",
        "config_update_auto": "Buscar actualizaciones al iniciar",
        "config_update_prerelease": "Incluir pre-releases (RC)",
        "config_check_updates_now": "Buscar actualizaciones ahora",
        "desktop_setup_title": "Lanzador de escritorio",
        "desktop_setup_first_body": (
            "¿Deseas crear un lanzador de BenchSim en el menú de aplicaciones?\n\n"
            "Ejecutable:\n{path}"
        ),
        "desktop_setup_update_body": (
            "La ruta del ejecutable de BenchSim cambió.\n"
            "¿Deseas actualizar el lanzador a la nueva ruta?\n\n"
            "Ejecutable:\n{path}"
        ),
        "desktop_setup_done": "Lanzador de escritorio instalado.",
        "desktop_setup_error": "No se pudo instalar el lanzador: {error}",
        "desktop_setup_error_icon": "No se encontró el archivo de icono de la aplicación.",
        "popup_error_title": "Error",
        "popup_warning_title": "Advertencia",
        "popup_info_title": "Información",
        "msg_folder_invalid": "La carpeta de proyecto no está definida o no existe.",
        "msg_iverilog_invalid": "La ruta de Icarus Verilog no es válida.",
        "msg_gtkwave_invalid": "La ruta de GTKWave no es válida.",
        "msg_no_sources": "No se encontraron archivos .v para compilar.",
        "msg_no_compile_files": "No hay archivos fuente para compilar en el proyecto seleccionado.",
        "msg_multiple_icestudio": (
            "Se detectaron varios subproyectos en ice-build. "
            "Abre directamente la carpeta del proyecto, por ejemplo: ice-build/<nombre_proyecto>/"
        ),
        "msg_compile_error": "<b>Error en la compilación:</b><br/><pre>{stderr}</pre>",
        "msg_sim_error": "<b>Error en la simulación:</b><br/><pre>{stderr}</pre>",
        "msg_no_vcd": "La simulación terminó, pero no se encontró archivo .vcd.",
        "msg_gtkw_config_error": "No se pudo generar configuración de GTKWave.",
        "msg_compiling": "<b>Compilando...</b><br/>archivos={count} modo={mode}<br/>",
        "msg_running": "<b>Ejecutando simulación...</b><br/>",
        "msg_opening_gtkw": "<b>Abriendo GTKWave...</b><br/>{cmd}<br/>",
        "msg_gtkw_running": "<b>GTKWave ya está en ejecución.</b><br/>VCD: {vcd}<br/>",
        "msg_sim_updated": "Simulación actualizada",
        "msg_gtkw_restarting": "<b>Recargando GTKWave con la simulación actualizada...</b><br/>",
        "msg_gtkw_closing": "<b>Cerrando GTKWave...</b><br/>",
        "msg_gtkw_closed": "<b>GTKWave cerrado.</b><br/>",
        "msg_gtkw_close_error": "<pre style='color:#E57373'>Error al cerrar GTKWave: {error}</pre>",
        "update_check_failed": "No se pudo verificar actualizaciones: {error}",
        "update_not_available": "BenchSim está actualizado ({version}).",
        "update_available_title": "Actualización disponible",
        "update_available_body": (
            "Versión actual: {current}\n"
            "Última versión: {latest}\n\n"
            "¿Abrir la página de release para descargar e instalar?"
        ),
    },
}


def normalize_lang(lang):
    """Return a supported language code."""
    if lang in TRANSLATIONS:
        return lang
    return DEFAULT_LANG


def tr(key, lang=None, **kwargs):
    """Translate key using selected language with fallback to English."""
    lang = normalize_lang(lang)
    text = TRANSLATIONS.get(lang, {}).get(key)
    if text is None:
        text = TRANSLATIONS[DEFAULT_LANG].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text
