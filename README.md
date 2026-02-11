# BenchSim

BenchSim is a desktop app (PyQt6 + QScintilla) to compile and simulate Verilog testbenches with Icarus Verilog (`iverilog` + `vvp`) and visualize waveforms in GTKWave.

## Why BenchSim

- Works well for Icestudio students who need simulation with fewer manual steps.
- Also works for generic Verilog projects.
- Auto-detects project layout and supports multiple testbenches (`*_tb.v`).

## Repository Layout

- `benchsim/`: Python package source code.
- `pyproject.toml`: packaging metadata and CLI entry points.
- `packaging/pyinstaller/BenchSim.spec`: PyInstaller recipe for executable builds.
- `main.v`, `main_tb.v`: minimal Verilog example.
- `sim_icon_package/`: icon assets.

## Requirements

- Python 3.8+
- Icarus Verilog (`iverilog`, `vvp`)
- GTKWave

## Install (development)

```bash
pip install -e .
```

## Run

```bash
benchsim
```

or

```bash
python -m benchsim.main
```

## Usage

1. Configure tool paths (`iverilog` and `gtkwave`) in the app.
2. Select the project folder.
3. Choose source-discovery mode:
   - `Auto`: use Icestudio mode when `ice-build/` exists, otherwise Generic.
   - `Icestudio`: compile `.v` files from project root + `ice-build/**`.
   - `Generic`: compile `.v` files from project root.
4. Select testbench (`*_tb.v`), edit, save, and simulate.

## Build Executable

```bash
pyinstaller packaging/pyinstaller/BenchSim.spec
```
