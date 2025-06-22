# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import platform
from PyQt6.QtCore import QLibraryInfo

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

# Find the Qt platform plugins directory
qt_plugins_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
qt_platforms_dir = os.path.join(qt_plugins_dir, 'platforms')

ffmpeg_bin = os.path.join(os.curdir, 'main', 'resources', 'ffmpeg-bin')
alass_bin = os.path.join(os.curdir, 'main', 'resources', 'alass-bin')
ffsubsync_bin = os.path.join(os.curdir, 'main', 'resources', 'ffsubsync-bin')

datas = [
    (os.path.join(os.curdir, 'main', 'VERSION'), '.'),
    (os.path.join(os.curdir, 'main', 'assets'), 'assets'),
    (qt_platforms_dir, 'platforms'),
]

with open('main/VERSION', 'r') as f:
    version = f.read().strip()

# Only import VSVersionInfo on Windows, because it gives error when building in other OS's.
if platform.system() == 'Windows':
    from main.version import VSVersionInfo
else:
    VSVersionInfo = version

folder_name = f'AutoSubSync-v{version}'

a = Analysis(
    ['main/main.py'],
    pathex=[],
    binaries=[
        (ffmpeg_bin, 'resources/ffmpeg-bin'),
        (alass_bin, 'resources/alass-bin'),
        (ffsubsync_bin, 'resources/ffsubsync-bin'),
    ],
    datas=datas,
    hiddenimports=[],
    #hookspath=['main/resources/hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

if platform.system() == 'Darwin':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='AutoSubSync',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        onefile=True,
        disable_windowed_traceback=True,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=os.path.join(os.curdir, 'main', 'assets', 'icon.icns'),
        info_plist={
            'CFBundleName': 'AutoSubSync',
            'CFBundleDisplayName': 'AutoSubSync',
            'CFBundleVersion': version,
            'CFBundleShortVersionString': version,
            'CFBundleIdentifier': 'com.denizsafak.AutoSubSync',
            'CFBundleExecutable': 'AutoSubSync',
            'CFBundleIconFile': 'icon.icns',
        }
    )
else:
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
        icon=os.path.join(os.curdir, 'main', 'assets', 'icon.ico'),
        version=VSVersionInfo,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=folder_name,
    )