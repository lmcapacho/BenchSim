# <img src="sim_icon_package/benchsim.png" alt="BenchSim icon" width="34" valign="middle"> BenchSim

BenchSim is a desktop app (PyQt6 + QScintilla) to edit, compile, and simulate Verilog testbenches using Icarus Verilog (`iverilog` + `vvp`) and visualize waveforms in GTKWave.

## Key Features

- Icestudio-oriented workflow (including `ice-build` project layouts).
- Generic Verilog workflow (plain folders with `.v` + `*_tb.v`).
- Auto-discovery of source files and testbenches.
- Console errors with clickable `file:line:col` navigation.
- Editor productivity:
  - Verilog autocomplete (keywords + symbols from current file).
  - Find/replace bar (`Ctrl+F`, `Ctrl+H`, `F3`, `Shift+F3`).
- Recent project folders integrated in the top toolbar.
- Built-in update checker (GitHub Releases).
- Linux first-run desktop launcher setup for packaged builds.

## Repository Layout

- `benchsim/`: application source code.
- `packaging/pyinstaller/BenchSim.spec`: executable build recipe.
- `packaging/linux/benchsim.desktop`: desktop entry template.
- `packaging/windows/BenchSim.iss`: Inno Setup installer script (Start Menu/Desktop shortcuts).
- `sim_icon_package/`: icon source/assets.
- `main.v`, `main_tb.v`: minimal Verilog example.

## Requirements

- Python 3.8+
- Icarus Verilog (`iverilog`, `vvp`)
- GTKWave

## Install (Development)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run (Development)

```bash
benchsim
```

or

```bash
python -m benchsim.main
```

## Project Modes

BenchSim supports 3 discovery modes:

- `Auto`
  Detects `Icestudio` when an `ice-build/` folder exists, otherwise uses `Generic`.
- `Icestudio`
  Searches Verilog sources in project root and `ice-build/**`, and supports `*_tb.v` in root or inside `ice-build/**`.
  If multiple Icestudio subprojects exist, open a specific folder such as:
  `ice-build/<project_name>/`
- `Generic`
  Uses `.v` and `*_tb.v` files from the selected folder.

## Icestudio Usage (Recommended)

1. Export your design from Icestudio (this generates `main.v` under `ice-build/<project_name>/`).
2. Place your testbench (`*_tb.v`, e.g. `main_tb.v`) in:
   - project root, or
   - `ice-build/<project_name>/` (recommended for multi-project setups).
3. In BenchSim, open either:
   - the main project folder (single Icestudio project), or
   - directly `ice-build/<project_name>/` (multiple projects).
4. Click `Simulate` (auto-saves first).

## Generic Verilog Usage

1. Put your DUT/source `.v` files and one or more `*_tb.v` files in the same folder.
2. Open that folder in BenchSim.
3. Select testbench and click `Simulate`.

## Shortcuts

- `Ctrl+S`: Save
- `Ctrl+R`: Simulate (auto-save + run)
- `Ctrl+Shift+V`: Validate project
- `Ctrl+F`: Find
- `Ctrl+H`: Replace
- `F3` / `Shift+F3`: Find next / previous
- `Ctrl+Space`: Trigger autocomplete

## Build Executable

Use the provided PyInstaller spec:

```bash
source .venv/bin/activate
python -m PyInstaller packaging/pyinstaller/BenchSim.spec --noconfirm --clean
```

Output is `onedir`:

- executable: `dist/BenchSim/BenchSim`
- runtime/libs: `dist/BenchSim/_internal/`

Important: distribute/run the whole `dist/BenchSim/` folder, not only the `BenchSim` binary.

## Linux Notes

- For packaged Linux builds, BenchSim can create/update a desktop launcher on first run.
- The launcher is written to:
  - `~/.local/share/applications/benchsim.desktop`
- Icons are copied to:
  - `~/.local/share/icons/hicolor/256x256/apps/benchsim.png`

## Windows Installer (Start Menu Entry)

BenchSim includes an Inno Setup script to create a Windows installer that adds:

- Start Menu shortcut (`Programs > BenchSim`)
- Optional Desktop shortcut
- Uninstaller entry in installed apps

### Steps

1. Build Windows executable first (on Windows):

```powershell
python -m PyInstaller packaging/pyinstaller/BenchSim.spec --noconfirm --clean
```

2. Install Inno Setup (if needed): https://jrsoftware.org/isinfo.php

3. Build installer from terminal:

```powershell
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\windows\BenchSim.iss
```

Installer output:

- `dist\installer\BenchSim-Setup-<version>.exe`
