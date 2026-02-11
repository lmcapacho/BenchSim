# BenchSim

Desktop application (PyQt6 + QScintilla) to compile and simulate Verilog projects with Icarus Verilog (`iverilog` + `vvp`) and open waveforms in GTKWave.

## Goal

The tool supports two workflows:

- Icestudio: designed for students exporting their design from Icestudio and simulating with minimal manual steps.
- Generic: for any Verilog project using a testbench.

## Requirements

- Python 3.8+
- Icarus Verilog (`iverilog`, `vvp`)
- GTKWave

## Installation (development mode)

```bash
cd verilog_simulator
pip install -e .
```

## Run

```bash
benchsim
```

or

```bash
python -m verilog_simulator.main
```

## Usage flow

1. Open the app and configure paths for `iverilog` and `gtkwave`.
2. Select the project folder.
3. Choose a source-discovery mode:
   - `Auto`: if `ice-build/` exists, use Icestudio profile; otherwise use Generic.
   - `Icestudio`: compile `.v` files from project root + `ice-build/**`.
   - `Generic`: compile `.v` files from project root.
4. Select the testbench (`*_tb.v`) in the selector.
5. Edit, save, and run simulation.

## Icestudio notes

- Keeps backward compatibility by preferring `main_tb.v` when available.
- If multiple testbenches exist, you can choose any of them.

## Structure

- `verilog_simulator/main.py`: main UI (`BenchSim`).
- `verilog_simulator/simulation_manager.py`: source discovery, compile, run, GTKWave launch.
- `verilog_simulator/settings_manager.py`: config persistence.
- `verilog_simulator/settings_dialog.py`: tool-path configuration.
- `verilog_simulator/editor.py`: Verilog editor.
- `verilog_simulator/message_dispatcher.py`: console/toast/popup messaging.
