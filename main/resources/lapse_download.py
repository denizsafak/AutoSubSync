import io
import os
import stat
import shutil
import platform
import tarfile
import zipfile
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
LAPSE_VERSION = "v2.0.1"
LAPSE_GITHUB_URL = f"https://github.com/Schwponaco-org/lapse/releases/download/{LAPSE_VERSION}"
DIST_BIN_PATH = os.path.join(script_dir, "lapse")


def get_archive_filename():
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine in ("x86_64", "x64", "amd64"):
        machine = "amd64"
    elif machine in ("aarch64", "armv8l", "arm64"):
        machine = "arm64"

    os_arch_map = {
        "windows": {
            "amd64": "lapse-windows-x64.zip",
            "arm64": "lapse-windows-x64.zip",  # Runs via x64 emulation on Windows on ARM
        },
        "darwin": {
            "arm64": "lapse-macos-arm64.tar.gz",
            "amd64": "lapse-macos-x86_64.tar.gz",
        },
        "linux": {
            "amd64": "lapse-linux-amd64.tar.gz",
            "arm64": "lapse-linux-arm64.tar.gz",
        },
    }

    try:
        return os_arch_map[system][machine]
    except KeyError:
        raise ValueError(f"Unsupported {system} ({machine}) architecture for lapse")


def get_binary_filename():
    """Alias for backwards compatibility."""
    return get_archive_filename()


def ensure_silero_vad():
    """Ensure silero_vad.onnx exists in DIST_BIN_PATH, downloading if necessary."""
    silero_path = os.path.join(DIST_BIN_PATH, "silero_vad.onnx")
    if os.path.isfile(silero_path):
        return silero_path
    download()
    return silero_path if os.path.isfile(silero_path) else None


def download():
    try:
        archive_name = get_archive_filename()
        download_url = f"{LAPSE_GITHUB_URL}/{archive_name}"
        print(f"Downloading lapse archive from {download_url}...")

        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        os.makedirs(DIST_BIN_PATH, exist_ok=True)
        content_bytes = response.content

        if archive_name.endswith(".tar.gz") or archive_name.endswith(".tgz"):
            with tarfile.open(fileobj=io.BytesIO(content_bytes), mode="r:gz") as tar:
                for member in tar.getmembers():
                    rel_name = os.path.basename(member.name)
                    if not rel_name:
                        continue
                    member_file = tar.extractfile(member)
                    if member_file:
                        target_path = os.path.join(DIST_BIN_PATH, rel_name)
                        with open(target_path, "wb") as out_f:
                            out_f.write(member_file.read())
        elif archive_name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(content_bytes)) as zf:
                for member in zf.infolist():
                    rel_name = os.path.basename(member.filename)
                    if not rel_name:
                        continue
                    with zf.open(member) as member_file:
                        target_path = os.path.join(DIST_BIN_PATH, rel_name)
                        with open(target_path, "wb") as out_f:
                            out_f.write(member_file.read())

        dest_filename = "lapse.exe" if platform.system().lower() == "windows" else "lapse"
        dest_path = os.path.join(DIST_BIN_PATH, dest_filename)

        if platform.system().lower() != "windows" and os.path.exists(dest_path):
            st = os.stat(dest_path)
            os.chmod(dest_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH | stat.S_IRWXU)

        # Ensure standard library symlinks / copies exist if versioned names were extracted
        for fname in os.listdir(DIST_BIN_PATH):
            full = os.path.join(DIST_BIN_PATH, fname)
            if "libonnxruntime" in fname and fname.endswith(".dylib") and fname != "libonnxruntime.dylib":
                std_dylib = os.path.join(DIST_BIN_PATH, "libonnxruntime.dylib")
                if not os.path.exists(std_dylib):
                    shutil.copy2(full, std_dylib)
            elif "libonnxruntime" in fname and ".so" in fname and fname != "libonnxruntime.so":
                std_so = os.path.join(DIST_BIN_PATH, "libonnxruntime.so")
                if not os.path.exists(std_so):
                    shutil.copy2(full, std_so)

        print(f"Downloaded and extracted lapse to {dest_path}")
        return dest_path
    except Exception as e:
        print(f"Error occurred while downloading lapse: {e}")
        raise


if __name__ == "__main__":
    try:
        download()
    except Exception:
        exit(1)

