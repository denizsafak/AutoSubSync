import sys
import os
import subprocess
import platform
import zipfile
import tarfile
import importlib.util
import json

def check_modules():
    required_modules = ['pip', 'tkinter', 'venv']
    for module in required_modules:
        try:
            importlib.import_module(module)
        except ImportError:
            if module == 'pip':
                sys.stderr.write("Module 'pip' is not installed. Please install it using your system's package manager.\n")
                sys.stderr.write("Debian: sudo apt-get install python3-pip python3-tk python3-venv\n")
                sys.stderr.write("Arch Linux: sudo pacman -S python python-pip tk\n")
                sys.stderr.write("Fedora: sudo dnf install python3-pip python3-tkinter python3-venv\n")
                sys.stderr.write("macOS: brew install python3 python-tk\n")
                sys.exit(1)
            elif module == 'tkinter':
                sys.stderr.write("Module 'tkinter' is not installed. Please install it using your system's package manager.\n")
                sys.stderr.write("Debian: sudo apt-get install python3-pip python3-tk python3-venv\n")
                sys.stderr.write("Arch Linux: sudo pacman -S python python-pip tk\n")
                sys.stderr.write("Fedora: sudo dnf install python3-pip python3-tkinter python3-venv\n")
                sys.stderr.write("macOS: brew install python3 python-tk\n")
                sys.exit(1)
            elif module == 'venv':
                sys.stderr.write("Module 'venv' is not installed. Please install it using your system's package manager.\n")
                sys.stderr.write("Debian: sudo apt-get install python3-pip python3-tk python3-venv\n")
                sys.stderr.write("Arch Linux: sudo pacman -S python python-pip tk\n")
                sys.stderr.write("Fedora: sudo dnf install python3-pip python3-tkinter python3-venv\n")
                sys.stderr.write("macOS: brew install python3 python-tk\n")
                sys.exit(1)
    print("All required modules are installed.")

def create_virtualenv():
    if not os.path.exists('venv'):
        print("Creating virtual environment...")
        completed_process = subprocess.run([sys.executable, '-m', 'venv', 'venv'], text=True)
        if completed_process.returncode != 0:
            print("Error creating virtual environment.")
            sys.exit(completed_process.returncode)
        print("Virtual environment created.")
    else:
        print("Virtual environment already exists. Skipping creation.")

def install_requirements():
    print("Installing requirements...")
    if platform.system() == 'Windows':
        pip_executable = 'venv\\Scripts\\pip'
    else:
        pip_executable = 'venv/bin/pip'
    completed_process = subprocess.run([pip_executable, 'install', '-r', 'main/requirements.txt', '--upgrade'], text=True)
    if completed_process.returncode != 0:
        print("Error installing requirements.")
        sys.exit(completed_process.returncode)
    print("Requirements installed.")

def ensure_ffmpeg():
    exe = '.exe' if platform.system() == 'Windows' else ''
    ffmpeg_dir = 'main/resources/ffmpeg-bin'
    
    if not all(os.path.exists(os.path.join(ffmpeg_dir, f'{app}{exe}')) 
               for app in ['ffmpeg', 'ffprobe']):
        print("FFmpeg executables not found, running ffmpeg_download.py...")
        if platform.system() == 'Windows':
            python_executable = 'venv\\Scripts\\python'
        else:
            python_executable = 'venv/bin/python'
        if subprocess.run([python_executable, 'main/resources/ffmpeg_download.py'], text=True).returncode != 0:
            print("Error downloading FFmpeg.")
            sys.exit(1)
        print("FFmpeg downloaded.")
    else:
        print("FFmpeg executables already exist. Skipping download.")
        
def ensure_ffsubsync():
    exe = '.exe' if platform.system() == 'Windows' else ''
    ffsubsync_dir = 'main/resources/ffsubsync-bin'
    
    if not os.path.exists(os.path.join(ffsubsync_dir, f'ffsubsync{exe}')):
        print("ffsubsync executable not found, running ffsubsync_bin_download.py...")
        if platform.system() == 'Windows':
            python_executable = 'venv\\Scripts\\python'
        else:
            python_executable = 'venv/bin/python'
        if subprocess.run([python_executable, 'main/resources/ffsubsync_bin_download.py'], text=True).returncode != 0:
            print("Error downloading ffsubsync.")
            sys.exit(1)
        print("ffsubsync downloaded.")
    else:
        print("ffsubsync executable already exists. Skipping download.")

def get_autosubsync_version():
    try:
        with open("main/VERSION", "r") as f:
            version = f.read().strip()
        print(f"Detected AutoSubSync version: {version}")
        return version
    except:
        return "unknown"

def get_ffmpeg_version():
    try:
        ffmpeg_path = os.path.join("main", "resources", "ffmpeg-bin", "ffmpeg.exe")
        result = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True)
        first_line = result.stdout.split('\n')[0]
        # Split by -www and take first part
        version = first_line.split('-www')[0].strip()
        # Print version info
        print(f"Detected FFmpeg version: {version}")
        return version
    except:
        return "unknown"

def get_ffsubsync_version():
    try:
        ffsubsync_path = os.path.join("main", "resources", "ffsubsync-bin", "ffsubsync.exe")
        result = subprocess.run([ffsubsync_path, "--version"], capture_output=True, text=True)
        version = result.stdout.strip()
        print(f"Detected ffsubsync version: {version}")
        return version
    except:
        return "unknown"

def get_alass_version():
    try:
        alass_path = os.path.join("main", "resources", "alass-bin", "alass-cli.exe")
        result = subprocess.run([alass_path, "--version"], capture_output=True, text=True)
        version = result.stdout.strip()
        print(f"Detected alass version: {version}")
        return version
    except:
        return "unknown"

def check_versions():
    if platform.system() == 'Windows':
        versions = {
            "AutoSubSync": get_autosubsync_version(),
            "ffmpeg": get_ffmpeg_version(),
            "ffsubsync": get_ffsubsync_version(),
            "alass": get_alass_version()
        }
        print("Writing versions to 'versions.json'...")
        with open(os.path.join("main", "resources", "versions.json"), "w") as f:
            json.dump(versions, f, indent=2)
    else:
        print("Skipping version check for non-Windows platform.")

def build_with_pyinstaller():
    print("Building with PyInstaller...")
    if platform.system() == 'Windows':
        pyinstaller_executable = 'venv\\Scripts\\pyinstaller'
    else:
        pyinstaller_executable = 'venv/bin/pyinstaller'
    completed_process = subprocess.run([pyinstaller_executable, '--clean', '-y', '--dist', './dist', 'build.spec'], text=True)
    if completed_process.returncode != 0:
        print("Error building with PyInstaller.")
        sys.exit(completed_process.returncode)
    print("Build completed.")
    
def create_archive():
    print("Creating archive...")
    with open('main/VERSION', 'r') as f:
        version = f.read().strip()
    
    dist_dir = 'dist'
    platform_name = platform.system().lower()
    arch = platform.machine().lower()
    
    if platform_name == 'linux':
        if arch == 'x86_64':
            arch = 'amd64'
        tar_name = f'AutoSubSync-v{version}-{platform_name}-{arch}.tar.gz'
        with tarfile.open(tar_name, 'w:gz') as tar:
            for root, _, files in os.walk(dist_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, dist_dir)
                    tar.add(file_path, arcname=arcname)
        print(f"Tar.gz archive created: {tar_name}")
    else:
        if platform_name == 'darwin':
            platform_name = 'macos'
        zip_name = f'AutoSubSync-v{version}-{platform_name}-{arch}.zip'
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(dist_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, dist_dir)
                    zipf.write(file_path, arcname)
        print(f"Zip archive created: {zip_name}")

if __name__ == '__main__':
    check_modules()
    create_virtualenv()
    install_requirements()
    ensure_ffmpeg()
    ensure_ffsubsync()
    check_versions()
    build_with_pyinstaller()
    create_archive()