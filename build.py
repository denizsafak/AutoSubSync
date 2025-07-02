import sys
import os
import subprocess
import platform
import zipfile
import tarfile
import importlib.util
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

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
    if platform.system() == "Windows":
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
    if platform.system() == "Windows":
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
    exe = ".exe" if platform.system() == "Windows" else ""
    ffmpeg_dir = "main/resources/ffmpeg-bin"
    if not all(os.path.exists(os.path.join(ffmpeg_dir, app + exe)) for app in apps):
        print("FFmpeg executables not found, running ffmpeg_download.py...")
        if platform.system() == "Windows":
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


def load_constants():
    """Load constants module using venv python"""
    try:
        if platform.system() == "Windows":
            python_executable = "venv\\Scripts\\python"
        else:
            python_executable = "venv/bin/python"
        
        # Create a small script to extract constants
        script = '''
import sys
import os
sys.path.insert(0, "main")
import constants
import json

data = {
    "VERSION": constants.VERSION,
    "SYNC_TOOLS": {}
}

for tool_name, tool_info in constants.SYNC_TOOLS.items():
    data["SYNC_TOOLS"][tool_name] = {
        "version": tool_info.get("version", "unknown"),
        "github": tool_info.get("github", "")
    }

print(json.dumps(data))
'''
        
        result = subprocess.run(
            [python_executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=script_dir
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"Error loading constants: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error loading constants: {e}")
        return None


def get_autosubsync_version():
    constants = load_constants()
    if constants:
        version = constants["VERSION"]
        print("Detected AutoSubSync version: " + version)
        return version
    return "unknown"


def get_ffmpeg_version():
    try:
        ffmpeg_path = os.path.join("main", "resources", "ffmpeg-bin", "ffmpeg")
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


def get_sync_tools_versions():
    """Get versions of sync tools from constants.py"""
    constants = load_constants()
    if constants:
        sync_tools_versions = {}
        for tool_name, tool_info in constants["SYNC_TOOLS"].items():
            version = tool_info.get("version", "unknown")
            github = tool_info.get("github", "")
            sync_tools_versions[tool_name] = {
                "version": version,
                "github": github
            }
            print(f"Detected {tool_name} version: {version}")
        return sync_tools_versions
    return {}


def check_versions():
    if platform.system() == "Linux":
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
        print("Skipping version check for non-Linux platform.")


def build_with_pyinstaller():
    print("Building with PyInstaller...")
    if platform.system() == "Windows":
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


def create_archive():
    print("Creating archive...")
    with open("main/VERSION", "r") as f:
        version = f.read().strip()

    dist_dir = "dist"
    platform_name = platform.system().lower()
    arch = platform.machine().lower()
    if arch == "x86_64":
        arch = "amd64"
    if platform_name == "linux":
        tar_name = (
            "AutoSubSync-v" + version + "-" + platform_name + "-" + arch + ".tar.gz"
        )
        with tarfile.open(tar_name, "w:gz") as tar:
            for root, _, files in os.walk(dist_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, dist_dir)
                    tar.add(file_path, arcname=arcname)
        print("Tar.gz archive created: " + tar_name)
        print("Full path: " + os.path.abspath(tar_name))
    elif platform_name == "darwin":
        platform_name = "macos"
        zip_name = "AutoSubSync-v" + version + "-" + platform_name + "-" + arch + ".zip"
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(dist_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join(
                        "AutoSubSync-v" + version, os.path.relpath(file_path, dist_dir)
                    )
                    zipf.write(file_path, arcname)
        print("Zip archive created: " + zip_name)
        print("Full path: " + os.path.abspath(zip_name))
    else:
        zip_name = "AutoSubSync-v" + version + "-" + platform_name + "-" + arch + ".zip"
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(dist_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, dist_dir)
                    zipf.write(file_path, arcname)
        print("Zip archive created: " + zip_name)
        print("Full path: " + os.path.abspath(zip_name))


if __name__ == "__main__":
    check_modules()
    create_virtualenv()
    install_requirements()
    remove_webrtcvad_hook()
    ensure_ffmpeg()
    check_versions()
    build_with_pyinstaller()
    create_archive()
