import io
import os
import platform
import shutil
import stat
import sys
import tarfile
import zipfile
import platformdirs
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
WHISPER_RELEASES_API = "https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=10"
BINARY_NAME = "whisper-cli.exe" if platform.system() == "Windows" else "whisper-cli"
DEFAULT_MODEL_NAME = "ggml-base.bin"
MODEL_URL = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{DEFAULT_MODEL_NAME}"

def _default_dist_bin_path():
    # A packaged or system-wide PyPI install can be read-only, so downloads fall back to the user's data folder
    return (
        os.path.join(platformdirs.user_data_dir("AutoSubSync", appauthor=False), "whisper")
        if getattr(sys, "frozen", False) or not os.access(script_dir, os.W_OK)
        else os.path.join(script_dir, "whisper")
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
    """Return the active directory for downloaded whisper-cli binaries."""
    # Preserve test or caller overrides applied directly to DIST_BIN_PATH
    if DIST_BIN_PATH != _INITIAL_DIST_BIN_PATH:
        return DIST_BIN_PATH
    utils = _get_utils_module()
    if utils is not None and utils.is_portable_mode():
        portable_dir = utils.get_portable_whisper_bin_dir()
        if portable_dir:
            return portable_dir
    return _default_dist_bin_path()


def get_model_dir():
    """Return the directory where the shared ggml model is stored."""
    if DIST_BIN_PATH != _INITIAL_DIST_BIN_PATH:
        return DIST_BIN_PATH
    utils = _get_utils_module()
    if utils is not None and utils.is_portable_mode():
        portable_model_dir = utils.get_portable_whisper_model_dir()
        if portable_model_dir:
            return portable_model_dir
    return get_dist_bin_path()


def _norm_machine():
    machine = platform.machine().lower()
    if machine in ("x86_64", "x64", "amd64"):
        return "amd64"
    if machine in ("aarch64", "armv8l", "arm64"):
        return "arm64"
    return machine


def get_archive_filename():
    system = platform.system().lower()
    machine = _norm_machine()
    os_arch_map = {
        "windows": {
            "amd64": "whisper-bin-x64.zip",
            "arm64": "whisper-bin-win-cpu-arm64.zip",
        },
        "linux": {
            "amd64": "whisper-bin-ubuntu-x64.tar.gz",
            "arm64": "whisper-bin-ubuntu-arm64.tar.gz",
        },
    }
    try:
        return os_arch_map[system][machine]
    except KeyError:
        raise ValueError(f"Unsupported {system} ({machine}) architecture for whisper-cli auto-download")


def installed_cli():
    """Return path to an installed whisper-cli binary, or None if not found."""
    local_cli = os.path.join(get_dist_bin_path(), BINARY_NAME)
    if os.path.isfile(local_cli):
        if os.name != "nt" and not os.access(local_cli, os.X_OK):
            try:
                os.chmod(
                    local_cli,
                    os.stat(local_cli).st_mode
                    | stat.S_IXUSR
                    | stat.S_IXGRP
                    | stat.S_IXOTH,
                )
            except OSError:
                pass
        return local_cli
    found = shutil.which(BINARY_NAME)
    if found:
        return found
    if platform.system() == "Darwin":
        for candidate in ("/opt/homebrew/bin/whisper-cli", "/usr/local/bin/whisper-cli"):
            if os.path.isfile(candidate):
                return candidate
    return None


def installed_model(model_name=DEFAULT_MODEL_NAME):
    """Return path to the downloaded whisper ggml model, or None if missing."""
    model_path = os.path.join(get_model_dir(), model_name)
    return model_path if os.path.isfile(model_path) and os.path.getsize(model_path) > 0 else None


def needs_download(model_name=DEFAULT_MODEL_NAME):
    """Return True if either whisper-cli or the ggml model is not yet installed."""
    return not (installed_cli() and installed_model(model_name))


def _resolve_cli_asset_url(archive_name):
    resp = requests.get(WHISPER_RELEASES_API, timeout=15)
    resp.raise_for_status()
    for release in resp.json():
        for asset in release.get("assets", []):
            if asset.get("name") == archive_name and asset.get("browser_download_url"):
                return asset["browser_download_url"]
    raise RuntimeError(f"Could not find {archive_name} in recent whisper.cpp releases")


def _is_runtime_file(filename):
    base = os.path.basename(filename)
    if base == BINARY_NAME:
        return True
    if platform.system() == "Windows":
        return base.lower().endswith(".dll")
    return ".so" in base


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


def download_cli(log_cb=None, progress_cb=None):
    """Download and extract whisper-cli and its shared libraries into DIST_BIN_PATH."""
    if platform.system() == "Darwin":
        existing = installed_cli()
        if existing:
            return existing
        raise RuntimeError(
            "whisper-cli auto-download is not available on macOS. "
            "Install it with 'brew install whisper-cpp' and try again."
        )

    if progress_cb is not None:
        progress_cb(-1)
    archive_name = get_archive_filename()
    url = _resolve_cli_asset_url(archive_name)
    if log_cb:
        log_cb(f"Downloading whisper-cli ({archive_name})...")

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    content_bytes = _read_response_bytes(response, progress_cb=progress_cb)
    if progress_cb is not None:
        progress_cb(-1)  # Extraction phase (indeterminate)

    dist_bin_path = get_dist_bin_path()
    os.makedirs(dist_bin_path, exist_ok=True)
    staging = dist_bin_path + ".cli.new"
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging)

    try:
        if archive_name.endswith(".tar.gz") or archive_name.endswith(".tgz"):
            deferred_links = []
            with tarfile.open(fileobj=io.BytesIO(content_bytes), mode="r:gz") as tar:
                for member in tar.getmembers():
                    if not _is_runtime_file(member.name):
                        continue
                    base = os.path.basename(member.name)
                    dest = os.path.join(staging, base)
                    if member.issym() or member.islnk():
                        target_base = os.path.basename(member.linkname)
                        if os.path.exists(dest) or os.path.islink(dest):
                            os.unlink(dest)
                        try:
                            os.symlink(target_base, dest)
                        except OSError:
                            # Filesystems such as FAT32/exFAT disallow symlinks; resolve via copy after extraction
                            deferred_links.append((dest, target_base))
                    elif member.isfile():
                        if os.path.islink(dest):
                            os.unlink(dest)
                        f = tar.extractfile(member)
                        if f is not None:
                            with open(dest, "wb") as out:
                                shutil.copyfileobj(f, out)
                            if base == BINARY_NAME:
                                os.chmod(
                                    dest,
                                    os.stat(dest).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
                                )
            if deferred_links:
                link_map = {os.path.basename(dest): target for dest, target in deferred_links}
                for dest, target_base in deferred_links:
                    seen = set()
                    cur = target_base
                    while cur in link_map and cur not in seen:
                        seen.add(cur)
                        cur = link_map[cur]
                    target_path = os.path.join(staging, cur)
                    if os.path.isfile(target_path) and not os.path.exists(dest):
                        shutil.copy2(target_path, dest)
        elif archive_name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(content_bytes)) as zf:
                for info in zf.infolist():
                    if info.is_dir() or not _is_runtime_file(info.filename):
                        continue
                    base = os.path.basename(info.filename)
                    dest = os.path.join(staging, base)
                    with zf.open(info) as src, open(dest, "wb") as out:
                        shutil.copyfileobj(src, out)

        cli_staged = os.path.join(staging, BINARY_NAME)
        if not os.path.isfile(cli_staged):
            raise RuntimeError(f"Downloaded archive {archive_name} did not contain {BINARY_NAME}")

        for entry in os.listdir(staging):
            src = os.path.join(staging, entry)
            dst = os.path.join(dist_bin_path, entry)
            if os.path.islink(dst) or os.path.isfile(dst):
                os.unlink(dst)
            shutil.move(src, dst)
        return os.path.join(dist_bin_path, BINARY_NAME)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def download_model(model_name=DEFAULT_MODEL_NAME, log_cb=None, progress_cb=None):
    """Stream-download the whisper ggml model into the active model dir atomically."""
    model_dir = get_model_dir()
    os.makedirs(model_dir, exist_ok=True)
    dest = os.path.join(model_dir, model_name)
    part = dest + ".part"
    url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{model_name}"
    if log_cb:
        log_cb(f"Downloading Whisper model ({model_name}, ~142 MB)...")

    try:
        with requests.get(url, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            try:
                total = int(resp.headers.get("content-length") or 0)
            except (AttributeError, TypeError, ValueError):
                total = 0
            downloaded = 0
            last_pct = -1
            last_log_pct = -25
            if progress_cb is not None:
                progress_cb(0 if total > 0 else -1)
            with open(part, "wb") as f:
                for chunk in resp.iter_content(chunk_size=262144):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = min(100, int(downloaded * 100 / total))
                            if progress_cb is not None and pct != last_pct:
                                last_pct = pct
                                progress_cb(pct)
                            if log_cb and pct >= last_log_pct + 25:
                                last_log_pct = pct
                                log_cb(
                                    f"Downloading {model_name}: {pct}% "
                                    f"({downloaded // (1024 * 1024)} / {total // (1024 * 1024)} MB)"
                                )
            if total > 0 and downloaded < total:
                raise RuntimeError(
                    f"Incomplete download for {model_name}: received {downloaded} of {total} bytes"
                )
            if progress_cb is not None and total <= 0:
                progress_cb(100)
        os.replace(part, dest)
        if log_cb:
            log_cb(f"Whisper model saved to {dest}")
    except Exception:
        if os.path.exists(part):
            os.unlink(part)
        raise
    return dest


def ensure_whisper(log_cb=None, progress_cb=None):
    """Ensure both whisper-cli and the default ggml model are available.

    Only called when the user enables the Whisper option for LAPSE.
    Returns (cli_path, model_path).
    """
    cli_path = installed_cli()
    if not cli_path:
        cli_path = download_cli(log_cb=log_cb, progress_cb=progress_cb)
        if log_cb:
            log_cb(f"whisper-cli ready: {cli_path}")
    model_path = installed_model()
    if not model_path:
        model_path = download_model(log_cb=log_cb, progress_cb=progress_cb)
    return cli_path, model_path
