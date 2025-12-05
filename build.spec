# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import platform
from PyQt6.QtCore import QLibraryInfo
import glob
import site
from PyInstaller.utils.hooks import collect_submodules

# =============================================================================
# Platform Detection and Configuration
# =============================================================================

CURRENT_PLATFORM = platform.system()
IS_WINDOWS = CURRENT_PLATFORM == 'Windows'
IS_MACOS = CURRENT_PLATFORM == 'Darwin'
IS_LINUX = CURRENT_PLATFORM == 'Linux'

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

# Collect all modules from the main package
# Include both 'main.module' and 'module' variants since code uses sys.path.insert
main_modules = collect_submodules('main')
main_modules_without_prefix = [m.replace('main.', '') for m in main_modules if m.startswith('main.')]
all_main_modules = main_modules + main_modules_without_prefix

# =============================================================================
# Qt Plugin Configuration
# =============================================================================

qt_plugins_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
qt_platforms_dir = os.path.join(qt_plugins_dir, 'platforms')

# =============================================================================
# Resource Paths
# =============================================================================

ffmpeg_bin = os.path.join(os.curdir, 'main', 'resources', 'ffmpeg-bin')
alass_bin = os.path.join(os.curdir, 'main', 'resources', 'alass-bin')
autosubsync = os.path.join(os.curdir, 'main', 'resources', 'autosubsync')
#ffsubsync_bin = os.path.join(os.curdir, 'main', 'resources', 'ffsubsync-bin')

# =============================================================================
# Data Files Configuration
# =============================================================================

datas = [
    (os.path.join(os.curdir, 'main', 'VERSION'), '.'),
    (os.path.join(os.curdir, 'main', 'assets'), 'assets'),
    (qt_platforms_dir, 'platforms'),
]

# Add all .dist-info folders from site-packages to datas for version detection
site_packages_dirs = site.getsitepackages()
for site_dir in site_packages_dirs:
    dist_infos = glob.glob(os.path.join(site_dir, '*.dist-info'))
    for dist_info in dist_infos:
        datas.append((dist_info, os.path.basename(dist_info)))

# =============================================================================
# Version Information
# =============================================================================

with open('main/VERSION', 'r') as f:
    version = f.read().strip()

# Only import version_info on Windows, because it gives error when building in other OS's
if IS_WINDOWS:
    from main.version import version_info
else:
    version_info = version

folder_name = 'AutoSubSync'

# =============================================================================
# Icon Paths (Platform-Specific)
# =============================================================================

def get_icon_path():
    """Return the appropriate icon path for the current platform."""
    if IS_WINDOWS:
        return os.path.join(os.curdir, 'main', 'assets', 'icon.ico')
    elif IS_MACOS:
        return os.path.join(os.curdir, 'main', 'assets', 'icon.icns')
    else:  # Linux
        return os.path.join(os.curdir, 'main', 'assets', 'icon.ico')

# =============================================================================
# Analysis
# =============================================================================

a = Analysis(
    ['main/main.py'],
    pathex=[os.path.join(os.getcwd(), 'main')],
    binaries=[
        (ffmpeg_bin, 'resources/ffmpeg-bin'),
        (alass_bin, 'resources/alass-bin'),
        (autosubsync, 'resources/autosubsync'),
    #    (ffsubsync_bin, 'resources/ffsubsync-bin'),
    ],
    datas=datas,
    hiddenimports=all_main_modules + [
        'ffsubsync',
        'autosubsync',
    ],
    #hookspath=['main/resources/hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# =============================================================================
# Platform-Specific Build Configuration
# =============================================================================

if IS_MACOS:
    # macOS: Create a .app bundle
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
        disable_windowed_traceback=True,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=get_icon_path(),
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

    app = BUNDLE(
        coll,
        name='AutoSubSync.app',
        icon=get_icon_path(),
        bundle_identifier='com.denizsafak.AutoSubSync',
        info_plist={
            'CFBundleName': 'AutoSubSync',
            'CFBundleDisplayName': 'AutoSubSync',
            'CFBundleVersion': version,
            'CFBundleShortVersionString': version,
            'CFBundleIdentifier': 'com.denizsafak.AutoSubSync',
            'CFBundleExecutable': 'AutoSubSync',
            'CFBundleIconFile': 'icon.icns',
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': '????',
            'LSMinimumSystemVersion': '10.13.0',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
        }
    )

elif IS_LINUX:
    # Linux: Create executable for AppImage packaging
    # The AppImage will be created by build.py using appimagetool
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
        icon=get_icon_path(),
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

else:
    # Windows: Standard executable with COLLECT
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
        icon=get_icon_path(),
        version=version_info,
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