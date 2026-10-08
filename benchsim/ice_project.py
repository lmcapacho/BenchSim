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
    INITIALIZATION_START = "// <BENCHSIM-DEFAULT-INITIALIZATION>"
    INITIALIZATION_END = "// </BENCHSIM-DEFAULT-INITIALIZATION>"
    CLOCK_START = "// <BENCHSIM-DEFAULT-CLOCK>"
    CLOCK_END = "// </BENCHSIM-DEFAULT-CLOCK>"

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
        initialization = self._render_initialization()
        clock = self._render_default_clock()
        return (
            "// BenchSim simulation scenario\n"
            f"// Design under test: {self.module_name}\n"
            "// Time scale: 1 ns / 1 ps. A delay of #1 equals 1 ns.\n"
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
            f"{initialization}\n\n"
            "    // Add your stimulus below this line.\n\n"
            "\n"
            "    // Default end time. Change or replace it with your own completion logic.\n"
            "    #100;\n"
            "    $finish;\n"
            "end\n"
            f"{clock}"
        )

    def _input_signals(self):
        """Return friendly names for the current DUT inputs."""
        return [signal for port, signal in self._signal_map() if port.direction == "input"]

    def _clock_signal(self):
        """Return the conventional clock input, if the interface exposes one."""
        return next((signal for signal in self._input_signals() if signal.lower() == "clk"), None)

    def _render_initialization(self, values=None):
        """Render generated defaults, preserving values for unchanged inputs."""
        values = values or {}
        lines = [
            f"    {self.INITIALIZATION_START}",
            "    // Default input values. Add custom setup below this block.",
        ]
        lines.extend(f"    {signal} = {values.get(signal, '0')};" for signal in self._input_signals())
        lines.append(f"    {self.INITIALIZATION_END}")
        return "\n".join(lines)

    def _render_default_clock(self):
        """Render a 10 ns default clock for an input explicitly named ``clk``."""
        clock = self._clock_signal()
        if not clock:
            return ""
        return (
            f"\n{self.CLOCK_START}\n"
            "// Generated clock: 10 ns period. Replace this block for custom timing.\n"
            f"always #5 {clock} = ~{clock};\n"
            f"{self.CLOCK_END}\n"
        )

    @staticmethod
    def _assignment_values(content, valid_signals):
        """Extract simple assignment values for signals still present in the DUT."""
        values = {}
        pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_$]*)\s*=\s*(.+?)\s*;\s*$", re.MULTILINE)
        for match in pattern.finditer(content):
            signal, value = match.groups()
            if signal in valid_signals:
                values[signal] = value
        return values

    @staticmethod
    def _replace_marked_block(content, start_marker, end_marker, replacement):
        """Replace one generated block, or return ``None`` when it is absent."""
        pattern = re.compile(
            rf"^[ \t]*{re.escape(start_marker)}\n.*?^[ \t]*{re.escape(end_marker)}\n?",
            re.MULTILINE | re.DOTALL,
        )
        if not pattern.search(content):
            return None
        return pattern.sub(replacement, content, count=1)

    def _refresh_initialization(self, content):
        """Update generated defaults while retaining values for unchanged inputs."""
        current_inputs = set(self._input_signals())
        if self.INITIALIZATION_START in content and self.INITIALIZATION_END in content:
            previous_values = self._assignment_values(content, current_inputs)
            replacement = self._render_initialization(previous_values)
            return self._replace_marked_block(
                content,
                self.INITIALIZATION_START,
                self.INITIALIZATION_END,
                replacement + "\n",
            )

        legacy_pattern = re.compile(
            r"^[ \t]*// Initial input values\..*?\n(?P<body>.*?)(?=^[ \t]*// Add your stimulus below this line\.)",
            re.MULTILINE | re.DOTALL,
        )
        legacy_match = legacy_pattern.search(content)
        if not legacy_match:
            return content
        body = legacy_match.group("body")
        unsupported = [
            line for line in body.splitlines()
            if line.strip() and not line.lstrip().startswith("//")
            and not re.match(r"^\s*[A-Za-z_][A-Za-z0-9_$]*\s*=\s*.+;\s*$", line)
        ]
        if unsupported:
            return content
        values = self._assignment_values(body, current_inputs)
        return content[: legacy_match.start()] + self._render_initialization(values) + "\n" + content[legacy_match.end():]

    def _refresh_default_clock(self, content):
        """Replace generated clocks when the clk port changes, preserving custom ones."""
        clock = self._clock_signal()
        marked_pattern = re.compile(
            rf"^{re.escape(self.CLOCK_START)}\n(?P<body>.*?)^{re.escape(self.CLOCK_END)}\n?",
            re.MULTILINE | re.DOTALL,
        )
        marked_match = marked_pattern.search(content)
        if marked_match:
            body = marked_match.group("body")
            if clock and re.search(rf"\b{re.escape(clock)}\s*=\s*~\s*{re.escape(clock)}\b", body):
                return content
            replacement = self._render_default_clock()
            return content[: marked_match.start()] + replacement + content[marked_match.end():]

        if not clock:
            return content
        existing_clock = re.search(
            rf"^\s*always\b[^\n]*\b{re.escape(clock)}\s*=\s*~\s*{re.escape(clock)}\b",
            content,
            re.MULTILINE,
        )
        if existing_clock:
            return content
        return content.rstrip() + "\n" + self._render_default_clock()

    def refresh_scenario_header(self, content):
        """Refresh generated interface, defaults, and clock without touching stimuli."""
        template = self.render_scenario_template()
        marker_end = "// </BENCHSIM-INTERFACE>"
        new_end = template.find(marker_end)
        if new_end < 0:
            return content
        new_header = template[: new_end + len(marker_end)]

        old_start = content.find("// BenchSim simulation scenario")
        old_end = content.find(marker_end)
        if old_start == 0 and old_end >= 0:
            content = new_header + content[old_end + len(marker_end):]
            content = self._refresh_initialization(content)
            return self._refresh_default_clock(content)

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
