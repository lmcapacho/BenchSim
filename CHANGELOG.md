# Changelog

All notable changes to BenchSim are documented in this file.

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
