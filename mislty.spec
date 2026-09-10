# -*- mode: python ; coding: utf-8 -*-
# ==============================================================================
# MisLTy Standalone Linux Executable Build Specification
# Purrfect Software Limited (PSL)
# ==============================================================================

import os
from pathlib import Path

block_cipher = None
project_root = Path(__file__).resolve().parent

added_datas = [
    (str(project_root / "src" / "mislty" / "gui" / "qml"), "mislty/gui/qml"),
    (str(project_root / "deploy" / "icons" / "mislty.svg"), "icons"),
    (str(project_root / "deploy" / "mislty.desktop"), "."),
]

hidden_imports = [
    "mislty",
    "mislty.audio",
    "mislty.audio.pcm_bridge",
    "mislty.cli",
    "mislty.cli.main",
    "mislty.core",
    "mislty.core.at_parser",
    "mislty.core.daemon",
    "mislty.core.port_resolver",
    "mislty.core.serial_transport",
    "mislty.core.sms",
    "mislty.core.urc_demuxer",
    "mislty.gui",
    "mislty.gui.app",
    "mislty.gui.tray",
    "mislty.ipc",
    "mislty.ipc.client",
    "mislty.ipc.dbus_service",
    "mislty.ipc.dispatcher",
    "mislty.net",
    "mislty.net.helper",
    "mislty.net.netns_mgr",
    "mislty.net.ppp_runner",
    "mislty.net.qcwebs_client",
    "mislty.net.wifi_mgr",
    "mislty.storage",
    "mislty.storage.database",
    "mislty.storage.metrics_store",
    "mislty.storage.sms_store",
    "sqlite3",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickLayouts",
    "PySide6.QtQuickControls2",
]

a = Analysis(
    [str(project_root / "src" / "mislty" / "cli" / "main.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "numpy"],
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
    name="mislty",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "deploy" / "icons" / "mislty.svg"),
)
