"""Tests for generated Icestudio simulation workspaces."""

import tempfile
import unittest
from pathlib import Path

from benchsim.ice_project import IcestudioProject


class IcestudioProjectTests(unittest.TestCase):
    """Verify interface parsing and scenario preservation."""

    def test_creates_wrapper_and_preserves_user_scenario(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ice_file = root / "counter.ice"
            ice_file.write_text("{}", encoding="utf-8")
            build_dir = root / "ice-build" / "counter"
            build_dir.mkdir(parents=True)
            main_v = build_dir / "main.v"
            main_v.write_text(
                """module main (
    input clk_v123abc,
    input [7:0] X_v456def,
    output [7:0] S_v654321,
    output [7:0] vinit
);
endmodule
""",
                encoding="utf-8",
            )

            project = IcestudioProject.discover(ice_file)
            workspace = project.ensure_testbench_workspace()
            scenario = workspace.scenario.read_text(encoding="utf-8")
            wrapper = workspace.wrapper.read_text(encoding="utf-8")

            self.assertIn("//   clk", scenario)
            self.assertIn("//   X [7:0]", scenario)
            self.assertIn("//   S [7:0]", scenario)
            self.assertNotIn("vinit", scenario)
            self.assertIn("reg clk;", wrapper)
            self.assertIn("wire [7:0] S;", wrapper)
            self.assertIn(".clk_v123abc(clk)", wrapper)

            workspace.scenario.write_text(
                scenario + "\ninitial begin\n    #5 X = 8'h2A;\nend\n",
                encoding="utf-8",
            )
            main_v.write_text(
                """module main (
    input clk_v123abc,
    input [7:0] X_v456def,
    input rst_v987654,
    output [7:0] S_v654321,
    output [7:0] vinit
);
endmodule
""",
                encoding="utf-8",
            )

            project.ensure_testbench_workspace()
            refreshed = workspace.scenario.read_text(encoding="utf-8")
            self.assertIn("//   rst", refreshed)
            self.assertIn("#5 X = 8'h2A;", refreshed)

