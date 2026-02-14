# -*- mode: python ; coding: utf-8 -*-
import os

# Some PyInstaller environments do not define __file__ in spec context.
spec_path = globals().get("__file__") or globals().get("SPEC")
if not spec_path:
    spec_path = os.path.join(os.getcwd(), "packaging", "pyinstaller", "BenchSim.spec")
spec_dir = os.path.dirname(os.path.abspath(spec_path))
project_root = os.path.abspath(os.path.join(spec_dir, "..", ".."))


a = Analysis(
    [os.path.join(project_root, 'benchsim', 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=[
        (os.path.join(project_root, 'benchsim', 'benchsim.ico'), 'benchsim'),
        (os.path.join(project_root, 'benchsim', 'benchsim.png'), 'benchsim'),
        (os.path.join(project_root, 'benchsim', 'themes', 'dark.qss'), 'benchsim/themes'),
        (os.path.join(project_root, 'benchsim', 'themes', 'light.qss'), 'benchsim/themes'),
        (os.path.join(project_root, 'benchsim', 'themes', 'editor_dark.json'), 'benchsim/themes'),
        (os.path.join(project_root, 'benchsim', 'themes', 'editor_light.json'), 'benchsim/themes'),
    ],
    hiddenimports=["PyQt6.sip", "PyQt6.Qsci"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='BenchSim',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    exclude_binaries=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=os.path.join(project_root, 'benchsim', 'benchsim.ico'),
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BenchSim',
)
