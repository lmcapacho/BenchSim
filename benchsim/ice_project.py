"""Discovery of the Verilog artifact associated with an Icestudio design."""

import json
import re
from dataclasses import dataclass
from pathlib import Path


class IcestudioProjectError(RuntimeError):
    """Raised when an Icestudio design cannot be resolved to generated Verilog."""


@dataclass(frozen=True)
class IcestudioProject:
    """An ``.ice`` file and the matching generated ``main.v`` artifact."""

    ice_file: Path
    build_dir: Path
    main_v: Path

    @classmethod
    def discover(cls, ice_file):
        """Resolve the standard Icestudio build directory for an ``.ice`` design."""
        source = Path(ice_file).expanduser().resolve()
        if not source.is_file() or source.suffix.lower() != ".ice":
            raise IcestudioProjectError("Select an Icestudio design file (.ice).")

        ice_build = source.parent / "ice-build"
        preferred = ice_build / source.stem
        for build_dir in (preferred, ice_build):
            main_v = build_dir / "main.v"
            if main_v.is_file():
                return cls(ice_file=source, build_dir=build_dir, main_v=main_v)

        expected = preferred / "main.v"
        raise IcestudioProjectError(
            f"{expected} does not exist. Export Verilog from Icestudio before opening this design."
        )

    @property
    def workspace_dir(self):
        """Return BenchSim-owned files kept separate from Icestudio artifacts."""
        return self.build_dir / ".benchsim"

    def ensure_testbench_workspace(self):
        """Create or refresh the generated wrapper without replacing user stimuli."""
        interface = VerilogInterface.discover(self.main_v)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        scenario = self.workspace_dir / "scenario.vh"
        wrapper = self.workspace_dir / "benchsim_tb.v"
        metadata = self.workspace_dir / "project.json"

        if not scenario.exists():
            scenario.write_text(interface.render_scenario_template(), encoding="utf-8", newline="\n")
        else:
            current_scenario = scenario.read_text(encoding="utf-8")
            refreshed_scenario = interface.refresh_scenario_header(current_scenario)
            if refreshed_scenario != current_scenario:
                scenario.write_text(refreshed_scenario, encoding="utf-8", newline="\n")
        wrapper.write_text(interface.render_wrapper(), encoding="utf-8", newline="\n")
        metadata.write_text(
            json.dumps(
                {
                    "version": 1,
                    "ice_file": str(self.ice_file),
                    "main_v": str(self.main_v),
                    "module": interface.module_name,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return BenchSimTestbenchWorkspace(scenario=scenario, wrapper=wrapper, metadata=metadata)


@dataclass(frozen=True)
class BenchSimTestbenchWorkspace:
    """Paths for one managed Icestudio testbench workspace."""

    scenario: Path
    wrapper: Path
    metadata: Path


@dataclass(frozen=True)
class VerilogPort:
    """One ANSI-style Verilog module port."""

    direction: str
    name: str
    width: str = ""


class VerilogInterface:
    """Small parser for the module interface required to generate a TB wrapper."""

    MODULE_RE = re.compile(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b")
    PORT_RE = re.compile(
        r"\b(input|output|inout)\b\s*(?:reg|wire|logic|signed|unsigned|tri|var|\s)*"
        r"(\[[^\]]+\])?\s*([A-Za-z_][A-Za-z0-9_$]*)",
        re.IGNORECASE,
    )
    RANDOM_SUFFIX_RE = re.compile(r"_(?:v|w)[0-9a-f]{6}$", re.IGNORECASE)
    HIDDEN_PORT_NAMES = {"vinit"}

    def __init__(self, module_name, ports):
        self.module_name = module_name
        self.ports = tuple(ports)

    @classmethod
    def discover(cls, source_path):
        """Read the first module header and extract its ANSI-style ports."""
        source = Path(source_path)
        content = source.read_text(encoding="utf-8")
        module_match = cls.MODULE_RE.search(content)
        if not module_match:
            raise IcestudioProjectError(f"No Verilog module was found in {source.name}.")

        header_end = cls._find_module_header_end(content, module_match.end())
        header = content[module_match.start():header_end]
        ports = []
        seen = set()
        for match in cls.PORT_RE.finditer(header):
            direction, width, name = match.groups()
            if name in seen:
                continue
            seen.add(name)
            ports.append(VerilogPort(direction.lower(), name, width or ""))
        if not ports:
            raise IcestudioProjectError(
                f"Could not read the module ports in {source.name}. Only ANSI-style Verilog ports are supported."
            )
        return cls(module_match.group(1), ports)

    @staticmethod
    def _find_module_header_end(content, start):
        """Find the terminating semicolon of a module header with nested parentheses."""
        depth = 0
        for index in range(start, len(content)):
            char = content[index]
            if char == "(":
                depth += 1
            elif char == ")" and depth:
                depth -= 1
            elif char == ";" and depth == 0:
                return index + 1
        raise IcestudioProjectError("The Verilog module header is incomplete.")

    @classmethod
    def _friendly_name(cls, port_name, used_names):
        name = cls.RANDOM_SUFFIX_RE.sub("", port_name) or port_name
        candidate = name
        suffix = 2
        while candidate in used_names:
            candidate = f"{name}_{suffix}"
            suffix += 1
        used_names.add(candidate)
        return candidate

    def _signal_map(self):
        used_names = set()
        return [
            (port, self._friendly_name(port.name, used_names))
            for port in self.ports
            if port.name.lower() not in self.HIDDEN_PORT_NAMES
        ]

    @staticmethod
    def _declaration(port, signal_name):
        width = f" {port.width}" if port.width else ""
        if port.direction == "input":
            return f"reg{width} {signal_name};"
        return f"wire{width} {signal_name};"

    def render_wrapper(self):
        """Return a generated testbench shell that includes the editable scenario."""
        signal_map = self._signal_map()
        declarations = "\n".join(
            f"    {self._declaration(port, signal)}" for port, signal in signal_map
        )
        connections = ",\n".join(
            f"        .{port.name}({signal})" for port, signal in signal_map
        )
        return (
            "`timescale 1ns/1ps\n\n"
            "// Generated by BenchSim from main.v. Do not edit this file.\n"
            "// Edit scenario.vh instead; it is preserved when main.v is re-exported.\n"
            "module benchsim_tb;\n"
            f"{declarations}\n\n"
            f"    {self.module_name} DUT (\n{connections}\n    );\n\n"
            "    initial begin\n"
            "        $dumpvars(0, benchsim_tb);\n"
            "    end\n\n"
            "    `include \"scenario.vh\"\n"
            "endmodule\n"
        )

    def render_scenario_template(self):
        """Return the editable starting point with current DUT interface documentation."""
        signal_map = self._signal_map()
        inputs = [
            f"//   {signal}{(' ' + port.width) if port.width else ''}"
            for port, signal in signal_map
            if port.direction == "input"
        ]
        outputs = [
            f"//   {signal}{(' ' + port.width) if port.width else ''}"
            for port, signal in signal_map
            if port.direction != "input"
        ]
        input_text = "\n".join(inputs) or "//   (none)"
        output_text = "\n".join(outputs) or "//   (none)"
        initial_values = "\n".join(f"    {signal} = 0;" for port, signal in signal_map if port.direction == "input")
        clock_signals = [signal for port, signal in signal_map if port.direction == "input" and signal.lower() == "clk"]
        clock_hint = ""
        if clock_signals:
            clock_hint = (
                "\n// Optional clock generator. Uncomment and adjust the period if needed.\n"
                f"// always #5 {clock_signals[0]} = ~{clock_signals[0]};\n"
            )
        return (
            "// BenchSim simulation scenario\n"
            f"// Design under test: {self.module_name}\n"
            "// <BENCHSIM-INTERFACE>\n"
            "// Inputs you can drive:\n"
            f"{input_text}\n"
            "//\n"
            "// Outputs you can observe in GTKWave:\n"
            f"{output_text}\n"
            "// </BENCHSIM-INTERFACE>\n"
            "// Add any valid testbench code below: initial, always, tasks, loops,\n"
            "// assertions, $display, $stop, and $finish.\n\n"
            "initial begin\n"
            "    // Initial input values. Change them if your test requires it.\n"
            f"{initial_values}\n\n"
            "    // Add your stimulus below this line.\n\n"
            "\n"
            "    // Default end time. Change or replace it with your own completion logic.\n"
            "    #100;\n"
            "    $finish;\n"
            "end\n"
            f"{clock_hint}"
        )

    def refresh_scenario_header(self, content):
        """Refresh generated interface comments without touching user test code."""
        template = self.render_scenario_template()
        marker_end = "// </BENCHSIM-INTERFACE>"
        new_end = template.find(marker_end)
        if new_end < 0:
            return content
        new_header = template[: new_end + len(marker_end)]

        old_start = content.find("// BenchSim simulation scenario")
        old_end = content.find(marker_end)
        if old_start == 0 and old_end >= 0:
            return new_header + content[old_end + len(marker_end):]

        legacy_default = (
            "// BenchSim simulation scenario\n"
            f"// Design under test: {self.module_name}\n"
        )
        if content.startswith(legacy_default) and "// Set initial input values and add your stimulus here." in content:
            legacy_initial = re.compile(
                r"\A.*?\binitial\s+begin\s*"
                r"// Set initial input values and add your stimulus here\.\s*"
                r"#100;\s*\$finish;\s*end\s*\Z",
                re.DOTALL,
            )
            if legacy_initial.match(content):
                return template

            initial_match = re.search(r"\binitial\s+begin\b", content)
            if initial_match:
                return new_header + "\n\n" + content[initial_match.start():]
        return content
