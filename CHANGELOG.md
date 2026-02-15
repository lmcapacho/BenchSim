# Changelog

All notable changes to BenchSim are documented in this file.

## [0.1.0] - 2026-02-15

### Added
- Verilog editor autocomplete for common keywords and document-local symbols.
- Integrated recent projects selector in the main toolbar.
- Find and replace workflow for faster editor navigation.
- Linux first-run desktop launcher setup, with stale launcher refresh.
- Windows installer support (Inno Setup script).
- Automated release workflow to generate Linux and Windows distributables.

### Changed
- Updated application and packaging icon assets.
- README expanded with release/build instructions and Icestudio usage guidance.
- Version aligned to stable `0.1.0`.
- UI action hierarchy simplified:
  - primary action as `Save & Simulate`
  - secondary `Validate` action.

### Fixed
- GTKWave restart flow to avoid hangs on repeated simulations.
- Global keyboard shortcuts for save, simulate, validate, and settings actions.
- PyInstaller runtime loading issues for frozen builds.
- Windows app icon association and installer architecture warnings.
- Dark/light theme contrast issues across editor tokens, checkboxes, comboboxes, and toolbar icons.
- Native/system icon handling on Windows and Linux with dark-theme visibility fallback.
- Update dialog formatting and version comparison behavior (`0.1.0rc1` vs `0.1.0`).
- Legacy `VerilogSimulator` naming traces removed from codebase.

## [0.1.0-rc1] - 2026-02-12

### Added
- Initial BenchSim project structure and packaging baseline.
- GitHub Actions CI workflow for install and smoke checks.
- `Validate` workflow in UI with compile-file preview.
- Configurable interface/message language (`English` and `Español`).
- Central i18n module (`benchsim/i18n.py`) for future translations.
- PyInstaller build spec at `packaging/pyinstaller/BenchSim.spec`.

### Changed
- Renamed app/project naming to BenchSim.
- Reorganized repository layout to standard package structure:
  - package in `benchsim/`
  - `pyproject.toml` at repository root
- Improved Icestudio source discovery and compile scoping.
- Compile only selected testbench when multiple `*_tb.v` files exist.
- Made `pyqttoast` optional to avoid installation failures.

### Fixed
- Fixed VCD macro define handling (`-DVCD_OUTPUT=simulation`).
- Fixed `NameError` in simulation logging path.
- Improved guidance when opening `ice-build/` root with multiple subprojects.
- Improved multi-project Icestudio conflict handling for `MAIN` port mismatches.
