# copied from https://github.com/qwqcode/ffsubsync-bin
import os
import platform
import requests
import io

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# URL base for downloading the latest FFmpeg binary
# FFMPEG_GITHUB_URL = "https://github.com/eugeneware/ffmpeg-static/releases/latest/download"

# This fork ↓ has a newer version of ffsubsync.
FFMPEG_GITHUB_URL = "https://github.com/davepagurek/ffmpeg-static/releases/latest/download"

DIST_BIN_PATH = 'ffmpeg-bin'

def get_zip_name(bin_name):
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine == 'x86_64': machine = 'amd64'

    os_arch_map = {
        'windows': {'amd64': f'{bin_name}-win32-x64.gz'},
        'darwin': {'arm64': f'{bin_name}-darwin-arm64.gz', 'amd64': f'{bin_name}-darwin-x64.gz'},
        'linux': {'amd64': f'{bin_name}-linux-x64.gz', 'arm64': f'{bin_name}-linux-arm64.gz'}
    }
    
    try:
        return os_arch_map[system][machine]
    except KeyError:
        raise ValueError(f"Unsupported {system} or {machine} architecture")

# Download and extract the FFmpeg binary
def download(bin_name):
    try:
        # Get system info to choose the right download
        zip_file_name = get_zip_name(bin_name)
        
        # Construct the download URL
        download_url = f"{FFMPEG_GITHUB_URL}/{zip_file_name}"
        print(f"Downloading {bin_name} from {download_url}...")
        
        # Send a GET request to the URL
        response = requests.get(download_url)
        response.raise_for_status()  # Check for request errors

        if zip_file_name.endswith('.gz'):
            import gzip
            import shutil
            with gzip.open(io.BytesIO(response.content), 'rb') as f_in:
                bin_name = f'{bin_name}.exe' if platform.system().lower() == 'windows' else bin_name
                with open(os.path.join(DIST_BIN_PATH, bin_name), 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
    except Exception as e:
        print(f"Error occurred: {e}")
        exit(1)

# Create necessary directory and run the download function
if not os.path.exists(DIST_BIN_PATH):
    os.makedirs(DIST_BIN_PATH)

# Execute the function to download and extract FFmpeg binary
download('ffmpeg')
download('ffprobe')
