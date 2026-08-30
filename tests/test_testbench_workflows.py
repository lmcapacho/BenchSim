"""Tests for testbench persistence, merging, and waveform setup."""

import tempfile
import unittest
from pathlib import Path

from benchsim.simulation_manager import SimulationManager
from benchsim.stimuli_persistence import StimuliPersistence
from benchsim.tb_merge_controller import TBMergeController


class _Screen:
    def width(self):
        return 1280

    def height(self):
        return 720


class TestbenchWorkflowTests(unittest.TestCase):
    """Verify persistence and simulation-view artifacts without a GUI."""

    def test_stimuli_parses_delay_and_assignment_in_order(self):
        content = """module main_tb;
reg [7:0] X;
initial begin
    X = 0;
    #1 X = 50;
    #(DURATION) X = 8'hFF;
    $finish;
end
endmodule
"""
        self.assertEqual(
            StimuliPersistence.parse_steps(content),
            [
                {"kind": "assign", "signal": "X", "value": "0"},
                {"kind": "delay", "time": "1"},
                {"kind": "assign", "signal": "X", "value": "50"},
                {"kind": "delay", "time": "(DURATION)"},
                {"kind": "assign", "signal": "X", "value": "8'hFF"},
            ],
        )

    def test_merges_non_overlapping_external_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tb_path = Path(temp_dir) / "main_tb.v"
            base = "reg a;\ninitial begin\n    a = 0;\nend\n"
            TBMergeController.ensure_snapshot(tb_path, base)
            TBMergeController.record_saved(tb_path, base.replace("a = 0", "a = 1"))

            result = TBMergeController.merge_external(
                tb_path,
                base.replace("reg a;", "reg a;\nreg b;"),
            )

            self.assertTrue(result.merged)
            self.assertIn("reg b;", result.content)
            self.assertIn("a = 1", result.content)

    def test_gtkwave_config_uses_direct_interface_in_declaration_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            vcd_path = folder / "dump.vcd"
            gtkw_path = folder / "simulation.gtkw"
            vcd_path.write_text(
                """$timescale 1ns $end
$scope module benchsim_tb $end
$var reg 1 ! clk $end
$var reg 1 \" rst $end
$var reg 8 # X [7:0] $end
$var wire 8 $ S [7:0] $end
$scope module DUT $end
$var wire 1 % internal $end
$upscope $end
$upscope $end
$enddefinitions $end
#0
0!
0\"
b00000000 #
b00000000 $
#100
1!
""",
                encoding="utf-8",
            )
            manager = SimulationManager.__new__(SimulationManager)
            self.assertTrue(
                manager.create_gtkw_config(
                    str(vcd_path),
                    str(gtkw_path),
                    _Screen(),
                    tb_top="benchsim_tb",
                    signal_order=["clk", "rst", "X", "S"],
                )
            )
            config = gtkw_path.read_text(encoding="utf-8")
            self.assertNotIn("internal", config)
            self.assertLess(config.index("benchsim_tb.clk"), config.index("benchsim_tb.rst"))
            self.assertLess(config.index("benchsim_tb.rst"), config.index("benchsim_tb.X[7:0]"))
            self.assertLess(config.index("benchsim_tb.X[7:0]"), config.index("benchsim_tb.S[7:0]"))

