# On Linux systems, you may need to install the following packages:
# sudo apt-get install python3-venv python3-pip python3-tk python3-requests

import sys
import os
import subprocess
import platform
import zipfile
import tarfile
import importlib.util

def check_modules():
    required_modules = ['tkinter', 'venv', 'requests']
    for module in required_modules:
        if importlib.util.find_spec(module) is None:
            if module in ['requests', 'venv']:
                print(f"Module '{module}' is not installed. Installing...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', module])
            else:
                sys.stderr.write(f"Module '{module}' is not installed.\n")
                sys.exit(1)
    print("All required modules are installed.")

def ensure_ffmpeg():
    exe = '.exe' if platform.system() == 'Windows' else ''
    ffmpeg_dir = 'main/resources/ffmpeg-bin'
    
    if not all(os.path.exists(os.path.join(ffmpeg_dir, f'{app}{exe}')) 
               for app in ['ffmpeg', 'ffprobe']):
        print("FFmpeg executables not found, running ffmpeg_download.py...")
        if subprocess.run([sys.executable, 'main/resources/ffmpeg_download.py'], text=True).returncode != 0:
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
        if subprocess.run([sys.executable, 'main/resources/ffsubsync_bin_download.py'], text=True).returncode != 0:
            print("Error downloading ffsubsync.")
            sys.exit(1)
        print("ffsubsync downloaded.")
    else:
        print("ffsubsync executable already exists. Skipping download.")

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
    ensure_ffmpeg()
    ensure_ffsubsync()
    create_virtualenv()
    install_requirements()
    build_with_pyinstaller()
    create_archive()