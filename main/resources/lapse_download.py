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
def _default_dist_bin_path():
    # A packaged or system-wide PyPI install can be read-only, so updates fall back to the user's data folder
    return (
        os.path.join(platformdirs.user_data_dir("AutoSubSync", appauthor=False), "lapse")
        if getattr(sys, "frozen", False) or not os.access(script_dir, os.W_OK)
        else os.path.join(script_dir, "lapse")
    )


DIST_BIN_PATH = _default_dist_bin_path()
_INITIAL_DIST_BIN_PATH = DIST_BIN_PATH


def _get_utils_module():
    try:
        import utils
        return utils
    except ImportError:
        try:
            from .. import utils
            return utils
        except ImportError:
            return None


def get_dist_bin_path():
    """Return the active directory for downloaded lapse binaries."""
    # Preserve test or caller overrides applied directly to DIST_BIN_PATH
    if DIST_BIN_PATH != _INITIAL_DIST_BIN_PATH:
        return DIST_BIN_PATH
    utils = _get_utils_module()
    if utils is not None and utils.is_portable_mode():
        portable_dir = utils.get_portable_lapse_bin_dir()
        if portable_dir:
            return portable_dir
    return _default_dist_bin_path()


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
    """Ensure silero_vad.onnx exists in the active lapse bin path, downloading if necessary."""
    silero_path = os.path.join(get_dist_bin_path(), "silero_vad.onnx")
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
    exe = os.path.join(get_dist_bin_path(), BINARY_NAME)
    if bundled and os.path.isfile(bundled) and not os.path.isfile(exe):
        return bundled
    if os.name != "nt" and os.path.isfile(exe) and not os.access(exe, os.X_OK):
        try:
            os.chmod(
                exe, os.stat(exe).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )
        except OSError:
            pass
    return exe


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


def _read_response_bytes(response, progress_cb=None):
    """Read response bytes, streaming chunks to report percentage progress when available."""
    try:
        total = int(response.headers.get("content-length") or 0)
    except (AttributeError, TypeError, ValueError):
        total = 0

    if progress_cb is not None:
        chunks = []
        downloaded = 0
        last_pct = -1
        if total > 0:
            progress_cb(0)
            last_pct = 0
        else:
            progress_cb(-1)
        for chunk in response.iter_content(chunk_size=262144):
            if not chunk:
                continue
            chunks.append(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = min(100, int(downloaded * 100 / total))
                if pct != last_pct:
                    last_pct = pct
                    progress_cb(pct)
        if chunks:
            if total > 0 and downloaded < total:
                raise RuntimeError(
                    f"Incomplete download: received {downloaded} of {total} bytes"
                )
            if total <= 0:
                progress_cb(100)
            return b"".join(chunks)
    return response.content


def download(progress_cb=None):
    dist_bin_path = get_dist_bin_path()
    os.makedirs(os.path.dirname(dist_bin_path), exist_ok=True)
    staging = dist_bin_path + ".new"
    try:
        archive_name = get_archive_filename()
        download_url = f"{LAPSE_RELEASES_URL}/download/{archive_name}"
        print(f"Downloading lapse archive from {download_url}...")

        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()

        # Unpack beside the old version so a bad download can't take it away
        shutil.rmtree(staging, ignore_errors=True)
        os.makedirs(staging)
        content_bytes = _read_response_bytes(response, progress_cb=progress_cb)
        if progress_cb is not None:
            progress_cb(-1)  # Extraction phase (indeterminate)

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

        if os.path.isdir(dist_bin_path):
            shutil.rmtree(dist_bin_path)
        os.replace(staging, dist_bin_path)
        dest_path = os.path.join(dist_bin_path, BINARY_NAME)
        print(f"Downloaded and extracted lapse to {dest_path}")
        return dest_path
    except Exception as e:
        shutil.rmtree(staging, ignore_errors=True)
        print(f"Error occurred while downloading lapse: {e}")
        raise


if __name__ == "__main__":
    try:
        if is_outdated(os.path.join(get_dist_bin_path(), BINARY_NAME)):
            download()
    except Exception:
        exit(1)

