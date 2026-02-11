"""Simulation orchestration for Icarus Verilog + GTKWave."""
import os
import re
import subprocess
import sys
from pathlib import Path

from vcdvcd import VCDVCD

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

    @staticmethod
    def _sorted_unique_paths(paths):
        return sorted(set(str(Path(path).resolve()) for path in paths if path))

    def discover_project_files(self, folder, mode="auto"):
        """Discover source and testbench files for both Icestudio and generic projects."""
        base = Path(folder).resolve()
        tb_files = sorted(str(path) for path in base.glob("*_tb.v"))

        effective_mode = mode or "auto"
        if effective_mode == "auto":
            effective_mode = "icestudio" if (base / self.ICE_BUILD_DIR).is_dir() else "generic"

        source_candidates = list(base.glob("*.v"))

        if effective_mode == "icestudio":
            ice_build = base / self.ICE_BUILD_DIR
            if ice_build.is_dir():
                source_candidates.extend(ice_build.rglob("*.v"))

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

    def run_simulation(self, screen_size, folder=None, mode="auto", tb_file=None):
        """Run compile/simulate/visualize pipeline."""
        messages = []
        config = self.settings.get_config()

        folder = (folder or config.get("verilog_folder", "")).strip()
        mode = (mode or config.get("project_mode", "auto")).strip() or "auto"
        iverilog = config.get("iverilog_path", "").strip()
        gtkwave = config.get("gtkwave_path", "").strip()

        if not folder or not os.path.isdir(folder):
            messages.append(
                create_message(
                    MessageType.ERROR,
                    "La carpeta de proyecto no está definida o no existe.",
                    extras=["popup"],
                )
            )
            return False, messages

        if not iverilog or not os.path.isfile(iverilog):
            messages.append(
                create_message(
                    MessageType.ERROR,
                    "La ruta de Icarus Verilog no es válida.",
                    extras=["popup"],
                )
            )
            return False, messages

        if not gtkwave or not os.path.isfile(gtkwave):
            messages.append(
                create_message(
                    MessageType.ERROR,
                    "La ruta de GTKWave no es válida.",
                    extras=["popup"],
                )
            )
            return False, messages

        discovery = self.discover_project_files(folder, mode=mode)
        source_files = discovery["source_files"]
        tb_files = discovery["tb_files"]

        if not source_files:
            messages.append(
                create_message(
                    MessageType.ERROR,
                    "No se encontraron archivos .v para compilar.",
                    extras=["popup"],
                )
            )
            return False, messages

        selected_tb = tb_file if tb_file in tb_files else discovery["preferred_tb"]
        if selected_tb and selected_tb not in source_files:
            source_files.append(selected_tb)
            source_files = self._sorted_unique_paths(source_files)

        output_file = os.path.join(folder, "simulation.out")
        gtkw_config = os.path.join(folder, "simulation.gtkw")

        iverilog_dir = os.path.dirname(iverilog)
        vvp_name = "vvp.exe" if os.name == "nt" else "vvp"
        vvp_path = os.path.join(iverilog_dir, vvp_name)
        if not os.path.isfile(vvp_path):
            vvp_path = vvp_name

        compile_cmd = [iverilog, "-o", output_file, '-DVCD_OUTPUT="simulation"', *source_files]
        sim_cmd = [vvp_path, output_file]

        messages.append(
            create_message(
                MessageType.LOG,
                f"<b>Compilando...</b><br/>archivos={len(source_files)} modo={discovery['effective_mode']}<br/>",
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
                    f"<b>Error en la compilación:</b><br/><pre>{compile_result.stderr}</pre>",
                    extras=["popup"],
                )
            )
            return False, messages

        previous_vcd_snapshot = {
            str(path.resolve()): path.stat().st_mtime for path in Path(folder).glob("*.vcd")
        }

        messages.append(create_message(MessageType.LOG, "<b>Ejecutando simulación...</b><br/>"))
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
                    f"<b>Error en la simulación:</b><br/><pre>{sim_result.stderr}</pre>",
                    extras=["popup"],
                )
            )
            return False, messages

        vcd_file = self._find_recent_vcd(folder, previous_vcd_snapshot)
        if not vcd_file:
            messages.append(
                create_message(
                    MessageType.ERROR,
                    "La simulación terminó, pero no se encontró archivo .vcd.",
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
                    "No se pudo generar configuración de GTKWave.",
                    extras=["popup"],
                )
            )
            return False, messages

        gtkwave_cmd = f'"{gtkwave}" "{gtkw_config}"'

        if self.gtkwave_thread and self.gtkwave_thread.isRunning():
            messages.append(create_message(MessageType.SUCCESS, "Simulación actualizada", extras=["toast"]))
            messages.append(
                create_message(
                    MessageType.LOG,
                    f"<b>GTKWave ya está en ejecución.</b><br/>VCD: {os.path.basename(vcd_file)}<br/>",
                )
            )
        else:
            messages.append(create_message(MessageType.LOG, f"<b>Abriendo GTKWave...</b><br/>{gtkwave_cmd}<br/>"))
            self.gtkwave_thread = ProcessRunner(gtkwave_cmd, cwd=folder)
            self.gtkwave_thread.start()

        return True, messages

    def close_gtkwave(self):
        """Terminate GTKWave process if it is still running."""
        messages = []
        if self.gtkwave_thread and self.gtkwave_thread.isRunning():
            messages.append(create_message(MessageType.LOG, "<b>Cerrando GTKWave...</b><br/>"))

            if sys.platform.startswith("win"):
                subprocess.run("taskkill /IM gtkwave.exe /F", shell=True, check=False)
            else:
                subprocess.run("pkill -f gtkwave", shell=True, check=False)

            if hasattr(self.gtkwave_thread, "process") and self.gtkwave_thread.process:
                try:
                    self.gtkwave_thread.process.kill()
                    self.gtkwave_thread.process.wait(timeout=3)
                    messages.append(create_message(MessageType.LOG, "<b>GTKWave cerrado.</b><br/>"))
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    messages.append(
                        create_message(
                            MessageType.LOG,
                            f"<pre style='color:#E57373'>Error al cerrar GTKWave: {exc}</pre>",
                        )
                    )

            self.gtkwave_thread.quit()
            self.gtkwave_thread.wait()
            self.gtkwave_thread = None

        return True, messages
