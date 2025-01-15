# -*- mode: python ; coding: utf-8 -*-

import os
import platform
import shutil

ffmpeg_bin = os.path.join(os.curdir, 'main', 'resources', 'ffmpeg-bin')
alass_bin = os.path.join(os.curdir, 'main', 'resources', 'alass-bin')

datas = [
    (os.path.join(os.curdir, 'main', 'resources', 'config.json'), '.'),
    (os.path.join(os.curdir, 'main', 'VERSION'), '.'),
    (os.path.join(os.curdir, 'main', 'settings.png'), '.')
]

# Define ffsubsync binary path based on OS
if platform.system() == 'Windows':
    ffsubsync_bin = os.path.join(os.curdir, 'venv', 'Scripts', 'ffs.exe')
    # Windows-specific DLL
    arch_bits = int(platform.architecture()[0][:2])
    if arch_bits == 64:
        datas.append((os.path.join(os.curdir, 'main', 'resources', 'VCRUNTIME140_1.dll'), '.'))
else:
    ffsubsync_bin = os.path.join(os.curdir, 'venv', 'bin', 'ffs')

a = Analysis(
    ['main/AutoSubSync.pyw'],
    pathex=[],
    binaries=[
        (ffmpeg_bin, 'resources/ffmpeg-bin'),
        (alass_bin, 'resources/alass-bin'),
        (ffsubsync_bin, '.')
    ],
    datas=datas,
    hiddenimports=['pkg_resources.py2_warn'],
    hookspath=['main/resources/hooks'],
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
    exclude_binaries=True,
    name='AutoSubSync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(os.curdir, 'main', 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoSubSync',
)