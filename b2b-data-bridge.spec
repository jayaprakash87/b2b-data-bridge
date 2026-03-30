# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — builds a single standalone binary.

Usage:
    pip install pyinstaller
    pyinstaller b2b-data-bridge.spec

Output: dist/b2b-data-bridge (or dist/b2b-data-bridge.exe on Windows)
"""

import sys
from pathlib import Path

block_cipher = None
src_root = str(Path("src"))

a = Analysis(
    [str(Path("src") / "b2b_data_bridge" / "main.py")],
    pathex=[src_root],
    binaries=[],
    datas=[],
    hiddenimports=[
        "b2b_data_bridge",
        "b2b_data_bridge.config",
        "b2b_data_bridge.models",
        "b2b_data_bridge.validation",
        "b2b_data_bridge.files",
        "b2b_data_bridge.sftp",
        "b2b_data_bridge.export",
        "b2b_data_bridge.orders",
        # pydantic internals that PyInstaller misses
        "pydantic",
        "pydantic.deprecated",
        "pydantic.deprecated.decorator",
        "pydantic._internal",
        "pydantic._internal._core_utils",
        "pydantic._internal._validators",
        "pydantic._internal._generate_schema",
        "pydantic._internal._generics",
        "annotated_types",
        "dotenv",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "scipy", "PIL"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="b2b-data-bridge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
