# -*- mode: python ; coding: utf-8 -*-
import os

project_root = os.path.abspath('.')


a = Analysis(
    ['benchsim/main.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        ('benchsim/sim.ico', 'benchsim'),
        ('benchsim/sim.png', 'benchsim'),
        ('benchsim/themes/dark.qss', 'benchsim/themes'),
    ],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='BenchSim',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon='benchsim/sim.ico',
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
