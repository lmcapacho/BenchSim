# benchsim

Repository for BenchSim development and packaging.

## Contents

- `verilog_simulator/`: Python package for the desktop app.
- `main.v`, `main_tb.v`: minimal example module + testbench.
- `sim_icon_package/`: icon assets.

## Project focus

- Make simulation easier for Icestudio users (especially students).
- Keep a clean and practical workflow for generic Verilog users.

## Current refactor scope

- Dual project modes: `Auto`, `Icestudio`, `Generic`.
- Testbench selector for `*_tb.v` files.
- More robust VCD detection after simulation.
- Correct package entry point: `verilog_simulator.main:main` (CLI: `benchsim`).

For setup and usage details, see `verilog_simulator/README.md`.
