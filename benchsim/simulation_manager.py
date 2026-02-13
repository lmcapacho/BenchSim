"""Simulation orchestration for Icarus Verilog + GTKWave."""
import os
import re
import subprocess
import sys
from pathlib import Path

from vcdvcd import VCDVCD

from .i18n import normalize_lang, tr
from .messages import MessageType, create_message
from .settings_manager import SettingsManager
from .simulation_runner import ProcessRunner

APP_NAME = "BenchSim"
LEGACY_APP_NAMES = ["VerilogSimulator"]


class SimulationManager:
    """Compile, run, and visualize Verilog simulations."""

    ICE_BUILD_DIR = "ice-build"

    def __init__(self):
        super().__init__()
        self.gtkwave_thread = None
        self.settings = SettingsManager(APP_NAME, legacy_app_names=LEGACY_APP_NAMES)

    def _stop_tracked_gtkwave(self):
        """Stop only the GTKWave process started by BenchSim, if any."""
        if not self.gtkwave_thread:
            return
        if hasattr(self.gtkwave_thread, "process") and self.gtkwave_thread.process:
            try:
                self.gtkwave_thread.process.terminate()
                self.gtkwave_thread.process.wait(timeout=1.5)
            except Exception:  # pylint: disable=broad-exception-caught
                try:
                    self.gtkwave_thread.process.kill()
                    self.gtkwave_thread.process.wait(timeout=1)
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
        self.gtkwave_thread.quit()
        # Never block UI indefinitely while trying to stop GTKWave.
        self.gtkwave_thread.wait(1200)
        self.gtkwave_thread = None

    @staticmethod
    def _sorted_unique_paths(paths):
        return sorted(set(str(Path(path).resolve()) for path in paths if path))

    def _guess_icestudio_scope(self, base, selected_tb=None):
        """Return the most likely Icestudio project scope directory."""
        ice_build = base / self.ICE_BUILD_DIR
        if not ice_build.is_dir():
            return base

        # If the selected testbench is inside ice-build, use its parent folder.
        if selected_tb:
            tb_path = Path(selected_tb).resolve()
            try:
                tb_path.relative_to(ice_build.resolve())
                return tb_path.parent
            except ValueError:
                pass

        project_dirs = [d for d in ice_build.iterdir() if d.is_dir()]
        if len(project_dirs) == 1:
            return project_dirs[0]

        # Fallback: if main.v exists directly under ice-build, use ice-build root.
        if (ice_build / "main.v").is_file():
            return ice_build

        return base

    def discover_project_files(self, folder, mode="auto"):
        """Discover source and testbench files for both Icestudio and generic projects."""
        base = Path(folder).resolve()

        effective_mode = mode or "auto"
        if effective_mode == "auto":
            effective_mode = "icestudio" if (base / self.ICE_BUILD_DIR).is_dir() else "generic"

        if effective_mode == "icestudio":
            # In Icestudio mode, allow testbench files either in project root
            # or inside per-project folders under ice-build.
            tb_candidates = list(base.glob("*_tb.v"))
            ice_build = base / self.ICE_BUILD_DIR
            if ice_build.is_dir():
                tb_candidates.extend(ice_build.rglob("*_tb.v"))
            tb_files = sorted(str(path.resolve()) for path in tb_candidates)
            source_candidates = list(base.glob("*.v"))
            if ice_build.is_dir():
                source_candidates.extend(ice_build.rglob("*.v"))
        else:
            tb_files = sorted(str(path.resolve()) for path in base.glob("*_tb.v"))
            source_candidates = list(base.glob("*.v"))

        source_files = [str(path.resolve()) for path in source_candidates]

        # Keep backward compatibility with Icestudio projects preferring main_tb.v.
        preferred_tb = None
        main_tb = str((base / "main_tb.v").resolve())
        if main_tb in tb_files:
            preferred_tb = main_tb
        elif tb_files:
            preferred_tb = tb_files[0]

        return {
            "effective_mode": effective_mode,
            "tb_files": self._sorted_unique_paths(tb_files),
            "source_files": self._sorted_unique_paths(source_files),
            "preferred_tb": preferred_tb,
        }

    @staticmethod
    def _extract_tb_top(tb_file):
        if not tb_file or not os.path.isfile(tb_file):
            return None

        with open(tb_file, "r", encoding="utf-8") as file:
            content = file.read()

        match = re.search(r"\bmodule\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", content)
        return match.group(1) if match else None

    @staticmethod
    def _find_recent_vcd(folder, previous_snapshot):
        base = Path(folder)
        current_vcds = {str(path.resolve()): path.stat().st_mtime for path in base.glob("*.vcd")}

        new_or_updated = [
            (path, mtime)
            for path, mtime in current_vcds.items()
            if path not in previous_snapshot or mtime > previous_snapshot[path]
        ]

        if new_or_updated:
            return max(new_or_updated, key=lambda item: item[1])[0]

        if current_vcds:
            return max(current_vcds.items(), key=lambda item: item[1])[0]

        return None

    def create_gtkw_config(self, vcd_path, gtkw_path, screen_size, tb_top=None):
        """Generate GTKWave save file with a useful signal set."""
        if not os.path.exists(vcd_path):
            return False

        vcd = VCDVCD(vcd_path, signals=None, store_tvs=False)
        exclude_pattern = re.compile(r"\.v[a-f0-9]{6,}|\.w\d+|\.vinit", re.IGNORECASE)

        reg_signals = set()
        wire_signals = set()
        all_signals = set()

        for signal in vcd.data.values():
            var_type = getattr(signal, "var_type", "")
            refs = getattr(signal, "references", [])

            for name in refs:
                if "DURATION" in name:
                    continue
                if exclude_pattern.search(name):
                    continue

                all_signals.add(name)

                if var_type == "reg":
                    reg_signals.add(name)
                elif var_type == "wire":
                    wire_signals.add(name)

        selected_regs = set()
        selected_wires = set()
        if tb_top:
            scope_prefix = f"{tb_top}."
            selected_regs = {name for name in reg_signals if name.startswith(scope_prefix)}
            selected_wires = {name for name in wire_signals if name.startswith(scope_prefix)}

        if not selected_regs and not selected_wires:
            selected_regs = reg_signals
            selected_wires = wire_signals

        if not selected_regs and not selected_wires:
            selected_wires = all_signals

        width, height = screen_size.width(), screen_size.height()

        with open(gtkw_path, "w", encoding="utf-8") as file:
            file.write(f'[dumpfile] "{os.path.basename(vcd_path)}"\n')
            file.write(f"[size] {width} {height}\n")

            for name in sorted(selected_regs):
                file.write(f"{name}\n")

            for name in sorted(selected_wires):
                file.write(f"{name}\n")

        return True

    def build_compile_plan(self, folder=None, mode="auto", tb_file=None, require_tools=False):
        """Build and validate compile inputs without executing the simulation."""
        messages = []
        config = self.settings.get_config()
        lang = normalize_lang(config.get("language", "en"))

        folder = (folder or config.get("verilog_folder", "")).strip()
        mode = (mode or config.get("project_mode", "auto")).strip() or "auto"
        iverilog = config.get("iverilog_path", "").strip()
        gtkwave = config.get("gtkwave_path", "").strip()

        if not folder or not os.path.isdir(folder):
            messages.append(
                create_message(
                    MessageType.ERROR,
                    tr("msg_folder_invalid", lang),
                    extras=["popup"],
                )
            )
            return False, messages, None

        if require_tools and (not iverilog or not os.path.isfile(iverilog)):
            messages.append(
                create_message(
                    MessageType.ERROR,
                    tr("msg_iverilog_invalid", lang),
                    extras=["popup"],
                )
            )
            return False, messages, None

        if require_tools and (not gtkwave or not os.path.isfile(gtkwave)):
            messages.append(
                create_message(
                    MessageType.ERROR,
                    tr("msg_gtkwave_invalid", lang),
                    extras=["popup"],
                )
            )
            return False, messages, None

        discovery = self.discover_project_files(folder, mode=mode)
        source_files = discovery["source_files"]
        tb_files = discovery["tb_files"]
        base_path = Path(folder).resolve()

        # Friendly guidance when user opens ice-build root with multiple projects.
        if not source_files and base_path.name == self.ICE_BUILD_DIR:
            project_dirs = [d for d in base_path.iterdir() if d.is_dir()]
            if len(project_dirs) > 1:
                messages.append(
                    create_message(
                        MessageType.ERROR,
                        tr("msg_multiple_icestudio", lang),
                        extras=["popup"],
                    )
                )
                return False, messages, None

        if not source_files:
            messages.append(
                create_message(
                    MessageType.ERROR,
                    tr("msg_no_sources", lang),
                    extras=["popup"],
                )
            )
            return False, messages, None

        selected_tb = tb_file if tb_file in tb_files else discovery["preferred_tb"]

        if discovery["effective_mode"] == "icestudio":
            scope_dir = self._guess_icestudio_scope(base_path, selected_tb=selected_tb)
            ice_build = base_path / self.ICE_BUILD_DIR
            project_dirs = [d for d in ice_build.iterdir() if d.is_dir()] if ice_build.is_dir() else []
            if scope_dir == base_path and len(project_dirs) > 1:
                messages.append(
                    create_message(
                    MessageType.ERROR,
                    tr("msg_multiple_icestudio", lang),
                    extras=["popup"],
                )
            )
                return False, messages, None

            scope_sources = [
                str(path.resolve())
                for path in scope_dir.rglob("*.v")
                if not path.name.endswith("_tb.v")
            ]
            if scope_sources:
                source_files = self._sorted_unique_paths(scope_sources)

        source_no_tb = [src for src in source_files if not Path(src).name.endswith("_tb.v")]
        compile_files = list(source_no_tb)
        if selected_tb:
            compile_files.append(selected_tb)
        compile_files = self._sorted_unique_paths(compile_files)

        if not compile_files:
            messages.append(
                create_message(
                    MessageType.ERROR,
                    tr("msg_no_compile_files", lang),
                    extras=["popup"],
                )
            )
            return False, messages, None

        plan = {
            "folder": folder,
            "mode": discovery["effective_mode"],
            "selected_tb": selected_tb,
            "compile_files": compile_files,
            "iverilog": iverilog,
            "gtkwave": gtkwave,
        }
        return True, messages, plan

    def run_simulation(self, screen_size, folder=None, mode="auto", tb_file=None):
        """Run compile/simulate/visualize pipeline."""
        lang = normalize_lang(self.settings.get_config().get("language", "en"))
        success, messages, plan = self.build_compile_plan(
            folder=folder,
            mode=mode,
            tb_file=tb_file,
            require_tools=True,
        )
        if not success:
            return False, messages
        folder = plan["folder"]
        selected_tb = plan["selected_tb"]
        compile_files = plan["compile_files"]
        iverilog = plan["iverilog"]
        gtkwave = plan["gtkwave"]

        output_file = os.path.join(folder, "simulation.out")
        gtkw_config = os.path.join(folder, "simulation.gtkw")

        iverilog_dir = os.path.dirname(iverilog)
        vvp_name = "vvp.exe" if os.name == "nt" else "vvp"
        vvp_path = os.path.join(iverilog_dir, vvp_name)
        if not os.path.isfile(vvp_path):
            vvp_path = vvp_name

        # Keep VCD_OUTPUT as a raw token (no quotes) so testbench macros like
        # `DUMPSTR(`VCD_OUTPUT)` from Icestudio expand correctly.
        compile_cmd = [iverilog, "-o", output_file, "-DVCD_OUTPUT=simulation", *compile_files]
        sim_cmd = [vvp_path, output_file]

        messages.append(
            create_message(
                MessageType.LOG,
                tr("msg_compiling", lang, count=len(compile_files), mode=plan["mode"]),
            )
        )

        compile_result = subprocess.run(
            compile_cmd,
            cwd=folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if compile_result.returncode != 0:
            messages.append(
                create_message(
                    MessageType.ERROR,
                    tr("msg_compile_error", lang, stderr=compile_result.stderr),
                    extras=["popup"],
                    data={"stage": "compile", "stderr": compile_result.stderr},
                )
            )
            return False, messages

        previous_vcd_snapshot = {
            str(path.resolve()): path.stat().st_mtime for path in Path(folder).glob("*.vcd")
        }

        messages.append(create_message(MessageType.LOG, tr("msg_running", lang)))
        sim_result = subprocess.run(
            sim_cmd,
            cwd=folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if sim_result.returncode != 0:
            messages.append(
                create_message(
                    MessageType.ERROR,
                    tr("msg_sim_error", lang, stderr=sim_result.stderr),
                    extras=["popup"],
                    data={"stage": "simulate", "stderr": sim_result.stderr},
                )
            )
            return False, messages

        vcd_file = self._find_recent_vcd(folder, previous_vcd_snapshot)
        if not vcd_file:
            messages.append(
                create_message(
                    MessageType.ERROR,
                    tr("msg_no_vcd", lang),
                    extras=["popup"],
                )
            )
            return False, messages

        tb_top = self._extract_tb_top(selected_tb)
        generated = self.create_gtkw_config(vcd_file, gtkw_config, screen_size, tb_top=tb_top)
        if not generated:
            messages.append(
                create_message(
                    MessageType.ERROR,
                    tr("msg_gtkw_config_error", lang),
                    extras=["popup"],
                )
            )
            return False, messages

        gtkwave_cmd = [gtkwave, gtkw_config]
        gtkwave_cmd_text = f'"{gtkwave}" "{gtkw_config}"'

        if self.gtkwave_thread and self.gtkwave_thread.isRunning():
            messages.append(create_message(MessageType.SUCCESS, tr("msg_sim_updated", lang), extras=["toast"]))
            messages.append(create_message(MessageType.LOG, tr("msg_gtkw_restarting", lang)))
            self._stop_tracked_gtkwave()

        messages.append(create_message(MessageType.LOG, tr("msg_opening_gtkw", lang, cmd=gtkwave_cmd_text)))
        self.gtkwave_thread = ProcessRunner(gtkwave_cmd, cwd=folder)
        self.gtkwave_thread.start()

        return True, messages

    def close_gtkwave(self):
        """Terminate GTKWave process if it is still running."""
        messages = []
        lang = normalize_lang(self.settings.get_config().get("language", "en"))
        if self.gtkwave_thread and self.gtkwave_thread.isRunning():
            messages.append(create_message(MessageType.LOG, tr("msg_gtkw_closing", lang)))

            if sys.platform.startswith("win"):
                subprocess.run("taskkill /IM gtkwave.exe /F", shell=True, check=False)
            else:
                subprocess.run("pkill -f gtkwave", shell=True, check=False)

            if hasattr(self.gtkwave_thread, "process") and self.gtkwave_thread.process:
                try:
                    self.gtkwave_thread.process.kill()
                    self.gtkwave_thread.process.wait(timeout=3)
                    messages.append(create_message(MessageType.LOG, tr("msg_gtkw_closed", lang)))
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    messages.append(
                        create_message(
                            MessageType.LOG,
                            tr("msg_gtkw_close_error", lang, error=exc),
                        )
                    )

            self.gtkwave_thread.quit()
            self.gtkwave_thread.wait()
            self.gtkwave_thread = None

        return True, messages
