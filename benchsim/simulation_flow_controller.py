"""Controller for validate/simulate UI flow orchestration."""

import os


class SimulationFlowController:
    """Handle validate and simulation actions from the main window."""

    def __init__(
        self,
        *,
        simulator,
        dispatcher,
        settings,
        project_selection,
        folder_path_getter,
        reset_problem_index,
        ensure_no_external_conflict,
        save_tb_file,
        get_screen_geometry,
        append_console,
        clear_console,
        append_problems,
        translate,
        language_getter,
    ):
        self.simulator = simulator
        self.dispatcher = dispatcher
        self.settings = settings
        self.project_selection = project_selection
        self.folder_path_getter = folder_path_getter
        self.reset_problem_index = reset_problem_index
        self.ensure_no_external_conflict = ensure_no_external_conflict
        self.save_tb_file = save_tb_file
        self.get_screen_geometry = get_screen_geometry
        self.append_console = append_console
        self.clear_console = clear_console
        self.append_problems = append_problems
        self._tr = translate
        self.language_getter = language_getter

    def validate_project(self):
        folder_path = self.folder_path_getter().strip()
        self.reset_problem_index()
        tb_path = self.project_selection.selected_tb_path()
        success, messages, plan = self.simulator.build_compile_plan(
            folder=folder_path,
            mode=self.project_selection.current_mode(),
            tb_file=tb_path,
            require_tools=True,
        )
        for message in messages:
            self.dispatcher.handle_message(message)
        if not success:
            return

        lang = self.language_getter()
        self.clear_console()
        self.append_console(self._tr("validation_preview_title", lang))
        self.append_console(
            self._tr(
                "validation_preview_meta",
                lang,
                mode=plan["mode"],
                tb=os.path.basename(plan["selected_tb"]) if plan["selected_tb"] else "N/A",
                count=len(plan["compile_files"]),
            )
        )
        for file_path in plan["compile_files"]:
            self.append_console(file_path)

        self.dispatcher.handle_message(
            {
                "type": "success",
                "message": self._tr(
                    "validation_success",
                    lang,
                    mode=plan["mode"],
                    tb=os.path.basename(plan["selected_tb"]) if plan["selected_tb"] else "N/A",
                    count=len(plan["compile_files"]),
                ),
                "extras": ["toast"],
            }
        )

    def run_simulation(self):
        self.clear_console()
        self.reset_problem_index()
        if not self.ensure_no_external_conflict():
            return

        screen_geometry = self.get_screen_geometry()
        if screen_geometry is None:
            self.append_console(self._tr("error_no_screen", self.language_getter()))
            return

        self.save_tb_file()

        folder_path = self.folder_path_getter().strip()
        tb_path = self.project_selection.selected_tb_path()
        success, messages = self.simulator.run_simulation(
            screen_geometry,
            folder=folder_path,
            mode=self.project_selection.current_mode(),
            tb_file=tb_path,
        )
        for message in messages:
            self.dispatcher.handle_message(message)
        self.append_problems(messages, folder_path)

        if success:
            self.settings.update_config(
                {
                    "verilog_folder": folder_path,
                    "project_mode": self.project_selection.current_mode(),
                    "selected_tb": tb_path or "",
                }
            )
            self.project_selection.add_recent_project(folder_path)
