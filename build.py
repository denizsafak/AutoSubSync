import sys
import os
import subprocess
import platform
import zipfile
import tarfile
import importlib.util
import json
import re
import ast
import shutil
import urllib.request
import stat

# =============================================================================
# Constants and Configuration
# =============================================================================

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

CURRENT_PLATFORM = platform.system()
IS_WINDOWS = CURRENT_PLATFORM == "Windows"
IS_MACOS = CURRENT_PLATFORM == "Darwin"
IS_LINUX = CURRENT_PLATFORM == "Linux"

# AppImage tool URL for Linux
APPIMAGETOOL_URL = "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"

# Add main directory to Python path to import constants and utils
sys.path.insert(0, os.path.join(script_dir, "main"))


def check_modules():
    required_modules = ["pip", "venv"]
    for module in required_modules:
        try:
            importlib.import_module(module)
        except ImportError:
            if module == "pip":
                sys.stderr.write(
                    "Module 'pip' is not installed. Please install it using your system's package manager.\n"
                )
                sys.stderr.write(
                    "Debian: sudo apt-get install python3-pip python3-venv\n"
                )
                sys.stderr.write("Arch Linux: sudo pacman -S python python-pip\n")
                sys.stderr.write(
                    "Fedora: sudo dnf install python3-pip python3-venv\n"
                )
                sys.stderr.write("macOS: brew install python3\n")
                sys.exit(1)
            elif module == "venv":
                sys.stderr.write(
                    "Module 'venv' is not installed. Please install it using your system's package manager.\n"
                )
                sys.stderr.write(
                    "Debian: sudo apt-get install python3-pip python3-venv\n"
                )
                sys.stderr.write("Arch Linux: sudo pacman -S python python-pip\n")
                sys.stderr.write(
                    "Fedora: sudo dnf install python3-pip python3-venv\n"
                )
                sys.stderr.write("macOS: brew install python3\n")
                sys.exit(1)
    print("All required modules are installed.")


def create_virtualenv():
    if not os.path.exists("venv"):
        print("Creating virtual environment...")
        completed_process = subprocess.run(
            [sys.executable, "-m", "venv", "venv"], text=True
        )
        if completed_process.returncode != 0:
            print("Error creating virtual environment.")
            sys.exit(completed_process.returncode)
        print("Virtual environment created.")
    else:
        print("Virtual environment already exists. Skipping creation.")


def install_requirements():
    print("Installing requirements...")
    if IS_WINDOWS:
        pip_executable = "venv\\Scripts\\pip"
    else:
        pip_executable = "venv/bin/pip"
    completed_process = subprocess.run(
        [pip_executable, "install", "-r", "main/requirements.txt", "--upgrade"],
        text=True,
    )
    if completed_process.returncode != 0:
        print("Error installing requirements.")
        sys.exit(completed_process.returncode)
    print("Requirements installed.")


def remove_webrtcvad_hook():
    if IS_WINDOWS:
        hook_path = os.path.join(
            "venv",
            "Lib",
            "site-packages",
            "_pyinstaller_hooks_contrib",
            "stdhooks",
            "hook-webrtcvad.py",
        )
        if os.path.exists(hook_path):
            try:
                os.remove(hook_path)
                print(f"Removed: {hook_path}")
            except Exception as e:
                print(f"Failed to remove {hook_path}: {e}")
        else:
            print(f"File not found, skipping: {hook_path}")


def ensure_ffmpeg():
    apps = ["ffmpeg", "ffprobe"]
    exe = ".exe" if IS_WINDOWS else ""
    ffmpeg_dir = "main/resources/ffmpeg-bin"
    if not all(os.path.exists(os.path.join(ffmpeg_dir, app + exe)) for app in apps):
        print("FFmpeg executables not found, running ffmpeg_download.py...")
        if IS_WINDOWS:
            python_executable = "venv\\Scripts\\python"
        else:
            python_executable = "venv/bin/python"
        if (
            subprocess.run(
                [python_executable, "main/resources/ffmpeg_download.py"], text=True
            ).returncode
            != 0
        ):
            print("Error downloading FFmpeg.")
            sys.exit(1)
        print("FFmpeg downloaded.")
    else:
        print("FFmpeg executables already exist. Skipping download.")


def get_version_info(module_name):
    """Return a version information of package using the venv Python."""
    if IS_WINDOWS:
        python_executable = os.path.join("venv", "Scripts", "python.exe")
    else:
        python_executable = os.path.join("venv", "bin", "python")
    try:
        result = subprocess.run(
            [python_executable, "-c", f"import importlib.metadata; print(importlib.metadata.version('{module_name}'))"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return "0.0"
    except Exception:
        return "0.0"


def get_autosubsync_version():
    try:
        with open(os.path.join("main", "VERSION"), "r") as f:
            version = f.read().strip()
            print("Detected AutoSubSync version: " + version)
            return version
    except Exception as e:
        print(f"Error reading AutoSubSync version: {e}")
        return "unknown"


def get_ffmpeg_version():
    try:
        ffmpeg_path = os.path.join("main", "resources", "ffmpeg-bin", "ffmpeg.exe")
        result = subprocess.run(
            [ffmpeg_path, "-version"], capture_output=True, text=True
        )
        first_line = result.stdout.split("\n")[0]
        # Extract version number from "ffmpeg version X.X.X-static"
        version_part = first_line.split(" ")[2]  # Get the third part
        version = version_part.split("-")[0]  # Remove "-static" or other suffixes
        print("Detected FFmpeg version: " + version)
        return version
    except:
        return "unknown"


def get_sync_tools_names_from_constants():
    """Parse constants.py using ast to extract SYNC_TOOLS dictionary top-level keys as a list of tool names."""
    constants_path = os.path.join(script_dir, "main", "constants.py")
    with open(constants_path, "r", encoding="utf-8") as f:
        content = f.read()
    tree = ast.parse(content, filename=constants_path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SYNC_TOOLS":
                    if isinstance(node.value, ast.Dict):
                        tool_names = []
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                                tool_names.append(key.value)
                        return tool_names
    return []


def get_sync_tools_versions():
    """Get versions of sync tools by parsing constants.py for tool names and using get_version_info or the version field for executables. Also extract github url if present."""
    constants_path = os.path.join(script_dir, "main", "constants.py")
    with open(constants_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=constants_path)
    sync_tools = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "SYNC_TOOLS" for t in node.targets
        ) and isinstance(node.value, ast.Dict):
            for key, value in zip(node.value.keys, node.value.values):
                if isinstance(key, ast.Constant) and isinstance(key.value, str) and isinstance(value, ast.Dict):
                    tool_name = key.value
                    tool_type = tool_version = github_url = None
                    for k, v in zip(value.keys, value.values):
                        if isinstance(k, ast.Constant):
                            if k.value == "type" and isinstance(v, ast.Constant):
                                tool_type = v.value
                            elif k.value == "version" and isinstance(v, ast.Constant):
                                tool_version = v.value
                            elif k.value == "github" and isinstance(v, ast.Constant):
                                github_url = v.value
                    sync_tools[tool_name] = {
                        "version": tool_version if tool_type == "executable" and tool_version else get_version_info(tool_name)
                    }
                    if github_url:
                        sync_tools[tool_name]["github"] = github_url
    for tool_name, info in sync_tools.items():
        print(f"Detected {tool_name} version: {info['version']}")
        if "github" in info:
            print(f"  GitHub: {info['github']}")
    return sync_tools


def check_versions():
    if IS_WINDOWS:
        versions = {
            "AutoSubSync": get_autosubsync_version(),
            "ffmpeg": get_ffmpeg_version(),
        }

        # Add sync tools versions
        sync_tools_versions = get_sync_tools_versions()
        if sync_tools_versions:
            versions["sync_tools"] = sync_tools_versions

        print("Writing versions to 'versions.json'...")
        with open(os.path.join("main", "resources", "versions.json"), "w") as f:
            json.dump(versions, f, indent=2)
    else:
        print("Skipping version check for non-Windows platform.")


def fix_macos_dylib_versions():
    """Fix macOS dylibs that lack proper SDK version info to prevent PyInstaller warnings."""
    if not IS_MACOS:
        return
    
    print("Checking for problematic macOS dylibs...")
    
    # Find dylibs in the virtual environment that may lack version info
    venv_site_packages = os.path.join(script_dir, "venv", "lib")
    
    # Find all dylib files
    problematic_dylibs = []
    for root, dirs, files in os.walk(venv_site_packages):
        for file in files:
            if file.endswith(".dylib"):
                dylib_path = os.path.join(root, file)
                # Check if the dylib has version info
                try:
                    result = subprocess.run(
                        ["otool", "-l", dylib_path],
                        capture_output=True,
                        text=True
                    )
                    # Check for LC_BUILD_VERSION or LC_VERSION_MIN_MACOSX
                    if "LC_BUILD_VERSION" not in result.stdout and "LC_VERSION_MIN_MACOSX" not in result.stdout:
                        problematic_dylibs.append(dylib_path)
                except Exception as e:
                    print(f"  Warning: Error checking {dylib_path}: {e}")
    
    if not problematic_dylibs:
        print("No problematic dylibs found.")
        return
    
    print(f"Found {len(problematic_dylibs)} dylib(s) without version info. Attempting to fix...")
    
    for dylib_path in problematic_dylibs:
        try:
            # Use vtool to add version info (available on macOS 11+)
            # This adds LC_BUILD_VERSION with macOS 10.13 as minimum
            result = subprocess.run(
                ["vtool", "-set-build-version", "macos", "10.13", "10.13", "-replace", "-output", dylib_path, dylib_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"  Fixed: {os.path.basename(dylib_path)}")
            else:
                print(f"  Warning: Could not fix {os.path.basename(dylib_path)}: {result.stderr}")
        except FileNotFoundError:
            # vtool not available, try alternative approach
            print(f"  Warning: vtool not available, skipping {os.path.basename(dylib_path)}")
        except Exception as e:
            print(f"  Warning: Error fixing {os.path.basename(dylib_path)}: {e}")


def build_with_pyinstaller():
    print("Building with PyInstaller...")
    if IS_WINDOWS:
        pyinstaller_executable = "venv\\Scripts\\pyinstaller"
    else:
        pyinstaller_executable = "venv/bin/pyinstaller"
    completed_process = subprocess.run(
        [pyinstaller_executable, "--clean", "-y", "--dist", "./dist", "build.spec"],
        text=True,
    )
    if completed_process.returncode != 0:
        print("Error building with PyInstaller.")
        sys.exit(completed_process.returncode)
    print("Build completed.")


# =============================================================================
# Linux AppImage Packaging
# =============================================================================

def download_appimagetool():
    """Download appimagetool if not present."""
    tools_dir = os.path.join(script_dir, "build_tools")
    os.makedirs(tools_dir, exist_ok=True)
    appimagetool_path = os.path.join(tools_dir, "appimagetool")
    
    if os.path.exists(appimagetool_path):
        print("appimagetool already exists.")
        return appimagetool_path
    
    print("Downloading appimagetool...")
    try:
        urllib.request.urlretrieve(APPIMAGETOOL_URL, appimagetool_path)
        # Make executable
        st = os.stat(appimagetool_path)
        os.chmod(appimagetool_path, st.st_mode | stat.S_IEXEC)
        print("appimagetool downloaded successfully.")
        return appimagetool_path
    except Exception as e:
        print(f"Error downloading appimagetool: {e}")
        return None


def create_appimage_structure():
    """Create the AppDir structure required for AppImage."""
    with open("main/VERSION", "r") as f:
        version = f.read().strip()
    
    folder_name = f"AutoSubSync-v{version}"
    appdir = os.path.join(script_dir, "dist", "AutoSubSync.AppDir")
    
    # Clean up existing AppDir
    if os.path.exists(appdir):
        shutil.rmtree(appdir)
    
    os.makedirs(appdir, exist_ok=True)
    
    # Copy the built application directly to AppDir (flat structure for PyInstaller apps)
    pyinstaller_output = os.path.join(script_dir, "dist", folder_name)
    if os.path.exists(pyinstaller_output):
        for item in os.listdir(pyinstaller_output):
            src = os.path.join(pyinstaller_output, item)
            dst = os.path.join(appdir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
    
    # Create AppRun script - simple launcher that runs the executable from AppDir
    apprun_content = '''#!/bin/bash
# AppRun script for AutoSubSync AppImage
SELF=$(readlink -f "$0")
HERE=${SELF%/*}

# Set library path to find bundled libraries
export LD_LIBRARY_PATH="${HERE}:${LD_LIBRARY_PATH}"

# Execute the main application
exec "${HERE}/AutoSubSync" "$@"
'''
    apprun_path = os.path.join(appdir, "AppRun")
    with open(apprun_path, "w") as f:
        f.write(apprun_content)
    st = os.stat(apprun_path)
    os.chmod(apprun_path, st.st_mode | stat.S_IEXEC)
    
    # Create .desktop file (required by AppImage specification)
    # Note: Version field in .desktop refers to Desktop Entry Spec version (1.0), not app version
    # App version can be included in Comment or X-AppImage-Version
    desktop_content = f'''[Desktop Entry]
Version=1.0
Name=AutoSubSync
GenericName=Automatic Subtitle Synchronizer
Exec=AutoSubSync %f
Icon=autosubsync
Type=Application
Categories=AudioVideo;Video;
Comment=Automatic subtitle synchronization tool.
Terminal=false
StartupWMClass=AutoSubSync
X-AppImage-Version={version}
'''
    desktop_path = os.path.join(appdir, "AutoSubSync.desktop")
    with open(desktop_path, "w") as f:
        f.write(desktop_content)
    
    # Copy PNG icon for AppImage (AppImage REQUIRES a PNG icon at the root of AppDir)
    icon_png_src = os.path.join(script_dir, "main", "assets", "icon.png")
    icon_dst = os.path.join(appdir, "autosubsync.png")
    
    if os.path.exists(icon_png_src):
        shutil.copy2(icon_png_src, icon_dst)
        print("PNG icon copied to AppDir.")
        
        # Create .DirIcon symlink (used by some file managers for folder icons)
        diricon_path = os.path.join(appdir, ".DirIcon")
        if os.path.exists(diricon_path) or os.path.islink(diricon_path):
            os.remove(diricon_path)
        os.symlink("autosubsync.png", diricon_path)
    else:
        print("ERROR: icon.png not found in main/assets/")
        print("       AppImage will work but won't display an icon.")
    
    return appdir


def build_appimage():
    """Build AppImage for Linux."""
    with open("main/VERSION", "r") as f:
        version = f.read().strip()
    
    print("Building AppImage for Linux...")
    
    # Download appimagetool if needed
    appimagetool = download_appimagetool()
    if not appimagetool:
        print("Error: Could not obtain appimagetool. Falling back to tar.gz archive.")
        return None
    
    # Create AppDir structure
    appdir = create_appimage_structure(version)
    
    # Build the AppImage
    machine_arch = platform.machine().lower()
    if machine_arch == "x86_64":
        arch = "amd64"
        appimagetool_arch = "x86_64"
    elif machine_arch == "aarch64":
        arch = "arm64"
        appimagetool_arch = "aarch64"
    else:
        arch = machine_arch
        appimagetool_arch = machine_arch
    
    appimage_name = f"AutoSubSync-v{version}-linux-{arch}.AppImage"
    appimage_path = os.path.join(script_dir, appimage_name)
    
    # Remove existing AppImage if present
    if os.path.exists(appimage_path):
        os.remove(appimage_path)
    
    print(f"Creating AppImage: {appimage_name}")
    
    # Set ARCH environment variable for appimagetool (requires x86_64/aarch64 format)
    env = os.environ.copy()
    env["ARCH"] = appimagetool_arch
    
    try:
        completed_process = subprocess.run(
            [appimagetool, "--appimage-extract-and-run", appdir, appimage_path],
            text=True,
            env=env,
            capture_output=True,
        )
        
        if completed_process.returncode != 0:
            print(f"appimagetool stderr: {completed_process.stderr}")
            print("Error creating AppImage. Falling back to tar.gz archive.")
            return None
        
        print(f"AppImage created successfully: {appimage_name}")
        print(f"Full path: {appimage_path}")
        
        # Clean up AppDir
        shutil.rmtree(appdir, ignore_errors=True)
        
        return appimage_path
        
    except Exception as e:
        print(f"Error running appimagetool: {e}")
        return None


# =============================================================================
# macOS .app Bundle Packaging
# =============================================================================

def sign_macos_app(app_path):
    """Ad-hoc sign the macOS app bundle to prevent Gatekeeper issues."""
    print("Signing macOS application bundle (ad-hoc)...")
    
    # First, clear any existing quarantine attributes
    try:
        subprocess.run(["xattr", "-cr", app_path], check=False)
        print("Cleared extended attributes.")
    except Exception as e:
        print(f"Warning: Could not clear xattr: {e}")
    
    # Ad-hoc sign the app bundle with deep signing and force
    # This signs all nested code (frameworks, helpers, etc.)
    try:
        result = subprocess.run(
            ["codesign", "--force", "--deep", "--sign", "-", app_path],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("App bundle signed successfully (ad-hoc).")
            return True
        else:
            print(f"Warning: Code signing failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("Warning: codesign not found. App may trigger Gatekeeper warnings.")
        return False
    except Exception as e:
        print(f"Warning: Code signing error: {e}")
        return False


def package_macos_app():
    """Package macOS .app bundle into a ZIP using ditto to preserve permissions and signatures."""
    with open("main/VERSION", "r") as f:
        version = f.read().strip()
    
    print("Packaging macOS application bundle...")
    
    app_path = os.path.join(script_dir, "dist", "AutoSubSync.app")
    
    if not os.path.exists(app_path):
        print(f"Error: Application bundle not found at {app_path}")
        return None
    
    # Sign the app bundle before packaging
    sign_macos_app(app_path)
    
    arch = platform.machine().lower()
    if arch == "x86_64":
        arch = "amd64"
    elif arch == "arm64":
        arch = "arm64"
    
    # Create a ZIP archive of the .app bundle using ditto
    # ditto preserves macOS-specific attributes, permissions, and code signatures
    zip_name = f"AutoSubSync-v{version}-macos-{arch}.zip"
    zip_path = os.path.join(script_dir, zip_name)
    
    # Remove existing zip if present
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    print(f"Creating ZIP archive: {zip_name}")
    
    # Use ditto to create the ZIP - this preserves permissions, symlinks, and signatures
    try:
        result = subprocess.run(
            ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", app_path, zip_path],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Error creating ZIP with ditto: {result.stderr}")
            return None
    except FileNotFoundError:
        print("Error: ditto command not found. This should only run on macOS.")
        return None
    
    print(f"ZIP archive created: {zip_name}")
    print(f"Full path: {zip_path}")
    
    return zip_path


# =============================================================================
# Windows Packaging
# =============================================================================

def package_windows():
    """Package Windows build into a ZIP archive."""
    with open("main/VERSION", "r") as f:
        version = f.read().strip()
    
    print("Packaging Windows application...")
    
    dist_dir = "dist"
    arch = platform.machine().lower()
    if arch == "amd64" or arch == "x86_64":
        arch = "amd64"
    
    zip_name = f"AutoSubSync-v{version}-windows-{arch}.zip"
    
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, dist_dir)
                zipf.write(file_path, arcname)
    
    print(f"ZIP archive created: {zip_name}")
    print(f"Full path: {os.path.abspath(zip_name)}")
    
    return zip_name


# =============================================================================
# Archive Creation (Platform-Specific)
# =============================================================================

def create_archive():
    """Create platform-specific archive/package."""
    print("Creating platform-specific package...")
    
    with open("main/VERSION", "r") as f:
        version = f.read().strip()
    
    if IS_LINUX:
        # Try to create AppImage, fall back to tar.gz
        result = build_appimage()
        if result is None:
            print("Falling back to tar.gz archive...")
            create_linux_tarball(version)
    elif IS_MACOS:
        # Package .app bundle
        package_macos_app()
    else:
        # Windows
        package_windows()


def create_linux_tarball(version):
    """Create a tar.gz archive for Linux (fallback if AppImage fails)."""
    dist_dir = "dist"
    arch = platform.machine().lower()
    if arch == "x86_64":
        arch = "amd64"
    
    tar_name = f"AutoSubSync-v{version}-linux-{arch}.tar.gz"
    
    with tarfile.open(tar_name, "w:gz") as tar:
        for root, _, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, dist_dir)
                tar.add(file_path, arcname=arcname)
    
    print(f"Tar.gz archive created: {tar_name}")
    print(f"Full path: {os.path.abspath(tar_name)}")


if __name__ == "__main__":
    check_modules()
    create_virtualenv()
    install_requirements()
    remove_webrtcvad_hook()
    ensure_ffmpeg()
    check_versions()
    fix_macos_dylib_versions()
    build_with_pyinstaller()
    create_archive()
