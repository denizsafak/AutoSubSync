import functools
import io
import os
import stat
import shutil
import sys
import platform
import subprocess
import tarfile
import zipfile
import platformdirs
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
LAPSE_RELEASES_URL = "https://github.com/Schwponaco-org/lapse/releases/latest"
BINARY_NAME = "lapse.exe" if platform.system() == "Windows" else "lapse"
# A packaged app can be read-only or signed, so its updates live in the user's data folder
DIST_BIN_PATH = (
    os.path.join(platformdirs.user_data_dir("AutoSubSync", appauthor=False), "lapse")
    if getattr(sys, "frozen", False)
    else os.path.join(script_dir, "lapse")
)


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


@functools.lru_cache(maxsize=None)
def latest_version():
    """The newest release, or None when offline. The redirect has no rate limit, unlike the API."""
    try:
        url = requests.head(LAPSE_RELEASES_URL, allow_redirects=True, timeout=10).url
    except requests.RequestException:
        return None
    return url.rsplit("/tag/v", 1)[-1] if "/tag/v" in url else None


def installed(bundled):
    """The binary to run: an update if we have one, otherwise the one shipped with the app."""
    exe = os.path.join(DIST_BIN_PATH, BINARY_NAME)
    return bundled if bundled and os.path.isfile(bundled) and not os.path.isfile(exe) else exe


def current_version(exe):
    """Empty when it can't run or is too old to have --version."""
    try:
        return subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def is_outdated(exe):
    found = current_version(exe)
    latest = latest_version()
    return not found or (latest is not None and found != latest)


def download():
    try:
        archive_name = get_archive_filename()
        download_url = f"{LAPSE_RELEASES_URL}/download/{archive_name}"
        print(f"Downloading lapse archive from {download_url}...")

        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()

        # Unpack beside the old version so a bad download can't take it away
        staging = DIST_BIN_PATH + ".new"
        shutil.rmtree(staging, ignore_errors=True)
        os.makedirs(staging)
        content_bytes = response.content

        if archive_name.endswith(".tar.gz") or archive_name.endswith(".tgz"):
            with tarfile.open(fileobj=io.BytesIO(content_bytes), mode="r:gz") as tar:
                for member in tar.getmembers():
                    rel_name = os.path.basename(member.name)
                    if not rel_name:
                        continue
                    member_file = tar.extractfile(member)
                    if member_file:
                        target_path = os.path.join(staging, rel_name)
                        with open(target_path, "wb") as out_f:
                            out_f.write(member_file.read())
        elif archive_name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(content_bytes)) as zf:
                for member in zf.infolist():
                    rel_name = os.path.basename(member.filename)
                    if not rel_name:
                        continue
                    with zf.open(member) as member_file:
                        target_path = os.path.join(staging, rel_name)
                        with open(target_path, "wb") as out_f:
                            out_f.write(member_file.read())

        dest_path = os.path.join(staging, BINARY_NAME)
        if not os.path.isfile(dest_path):
            raise RuntimeError(f"{archive_name} has no {BINARY_NAME} in it")

        if platform.system().lower() != "windows":
            st = os.stat(dest_path)
            os.chmod(dest_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH | stat.S_IRWXU)

        # Ensure standard library symlinks / copies exist if versioned names were extracted
        for fname in os.listdir(staging):
            full = os.path.join(staging, fname)
            if "libonnxruntime" in fname and fname.endswith(".dylib") and fname != "libonnxruntime.dylib":
                std_dylib = os.path.join(staging, "libonnxruntime.dylib")
                if not os.path.exists(std_dylib):
                    shutil.copy2(full, std_dylib)
            elif "libonnxruntime" in fname and ".so" in fname and fname != "libonnxruntime.so":
                std_so = os.path.join(staging, "libonnxruntime.so")
                if not os.path.exists(std_so):
                    shutil.copy2(full, std_so)

        if os.path.isdir(DIST_BIN_PATH):
            shutil.rmtree(DIST_BIN_PATH)
        os.replace(staging, DIST_BIN_PATH)
        dest_path = os.path.join(DIST_BIN_PATH, BINARY_NAME)
        print(f"Downloaded and extracted lapse to {dest_path}")
        return dest_path
    except Exception as e:
        print(f"Error occurred while downloading lapse: {e}")
        raise


if __name__ == "__main__":
    try:
        if is_outdated(os.path.join(DIST_BIN_PATH, BINARY_NAME)):
            download()
    except Exception:
        exit(1)

