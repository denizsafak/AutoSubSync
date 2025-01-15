import sys
import os
import subprocess
import platform
import zipfile

def ensure_ffmpeg():
    exe = '.exe' if platform.system() == 'Windows' else ''
    ffmpeg_dir = 'main/resources/ffmpeg-bin'
    
    if not all(os.path.exists(os.path.join(ffmpeg_dir, f'{app}{exe}')) 
               for app in ['ffmpeg', 'ffprobe']):
        print("FFmpeg executables not found, running ffmpeg_download.py...")
        if subprocess.run(['python', 'main/resources/ffmpeg_download.py'], text=True).returncode != 0:
            print("Error downloading FFmpeg.")
            sys.exit(1)
        print("FFmpeg downloaded.")
    else:
        print("FFmpeg executables already exist. Skipping download.")

def create_virtualenv():
    if not os.path.exists('venv'):
        print("Creating virtual environment...")
        completed_process = subprocess.run(['python', '-m', 'venv', 'venv'], text=True)
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
    completed_process = subprocess.run([pip_executable, 'install', '-r', 'main/requirements.txt'], text=True)
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

def create_zip():
    print("Creating zip archive...")
    with open('main/VERSION', 'r') as f:
        version = f.read().strip()
    
    dist_dir = 'dist'
    platform_name = platform.system().lower()
    arch = platform.machine().lower()
    zip_name = f'AutoSubSync-v{version}-{platform_name}-{arch}.zip'
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, dist_dir)
                zipf.write(file_path, arcname)
    print(f"Zip archive created: {zip_name}")

if __name__ == '__main__':
    ensure_ffmpeg()
    create_virtualenv()
    install_requirements()
    build_with_pyinstaller()
    create_zip()