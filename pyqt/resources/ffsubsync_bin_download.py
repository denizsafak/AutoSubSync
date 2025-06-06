import os
import platform
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# URL base for downloading the latest ffsubsync binary
FFSUBSYNC_GITHUB_URL = (
    "https://github.com/denizsafak/ffsubsync-bin-core/releases/latest/download"
)
DIST_BIN_PATH = "ffsubsync-bin"


def get_bin_name(bin_name):
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine == "x86_64":
        machine = "amd64"

    os_arch_map = {
        "windows": {"amd64": f"{bin_name}_win_amd64"},
        "darwin": {
            "arm64": f"{bin_name}_macos_arm64",
            "amd64": f"{bin_name}_macos_amd64",
        },
        "linux": {"amd64": f"{bin_name}_linux_amd64"},
    }

    try:
        return os_arch_map[system][machine]
    except KeyError:
        raise ValueError(f"Unsupported {system} or {machine} architecture")


# Download the ffsubsync binary
def download(bin_name):
    try:
        # Get system info to choose the right download
        bin_file_name = get_bin_name(bin_name)

        # Construct the download URL
        download_url = f"{FFSUBSYNC_GITHUB_URL}/{bin_file_name}"
        print(f"Downloading {bin_name} from {download_url}...")

        # Send a GET request to the URL
        response = requests.get(download_url)
        response.raise_for_status()  # Check for request errors

        bin_name = (
            "ffsubsync.exe" if platform.system().lower() == "windows" else "ffsubsync"
        )
        with open(os.path.join(DIST_BIN_PATH, bin_name), "wb") as f_out:
            f_out.write(response.content)

    except Exception as e:
        print(f"Error occurred: {e}")
        exit(1)


# Create necessary directory and run the download function
if not os.path.exists(DIST_BIN_PATH):
    os.makedirs(DIST_BIN_PATH)

# Execute the function to download ffsubsync binary
download("ffsubsync_bin")
