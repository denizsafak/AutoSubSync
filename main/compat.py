import ctypes
import ctypes.util
import importlib.util
import logging
import os
import platform
import sys
import types
import warnings
from pathlib import Path

"""
Compatibility layer for AutoSubSync.
Handles shims for deprecated or removed features in newer Python versions.
"""

logger = logging.getLogger(__name__)

# Keep a reference to the loaded libsndfile handle so the dynamic loader does
# not unload it after the compatibility check returns.
_soundfile_library_ready = False
_soundfile_library_handle = None
_sndfile_lookup_patched = False

# Shim for pkg_resources (removed in Python 3.14+)
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated as an API.*")
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        import pkg_resources
except ImportError:
    # Create a dummy pkg_resources module to satisfy legacy dependencies
    pkg_resources_shim = types.ModuleType("pkg_resources")

    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:
        from importlib_metadata import PackageNotFoundError, version  # type: ignore

    class DistributionNotFound(Exception):
        pass

    class _Distribution:
        def __init__(self, name, dist_version):
            self.project_name = name
            self.version = dist_version

    def resource_filename(package_or_requirement, resource_name):
        """
        Implementation of resource_filename for legacy libraries (like autosubsync).
        """
        try:
            module = sys.modules.get(package_or_requirement)
            if module and hasattr(module, "__file__") and module.__file__:
                return str(Path(module.__file__).parent / resource_name)
        except Exception:
            pass
        return resource_name

    def get_distribution(name):
        try:
            return _Distribution(name, version(name))
        except PackageNotFoundError as e:
            raise DistributionNotFound(name) from e

    def require(name):
        return [get_distribution(name)]

    pkg_resources_shim.resource_filename = resource_filename
    pkg_resources_shim.get_distribution = get_distribution
    pkg_resources_shim.require = require
    pkg_resources_shim.DistributionNotFound = DistributionNotFound
    sys.modules["pkg_resources"] = pkg_resources_shim


def _soundfile_library_candidates():
    """Yield libsndfile paths bundled by the maintained ``soundfile`` package.

    The abandoned ``PySoundFile`` distribution used by ``autosubsync`` looks
    for libsndfile next to ``soundfile.py`` but its universal wheel does not
    ship the library. Newer ``soundfile`` releases place self-contained
    binaries in a ``_soundfile_data`` directory. This helper locates those
    binaries without importing either package, because importing the legacy
    module would fail while the library is still missing.
    """
    search_dirs = []

    try:
        soundfile_spec = importlib.util.find_spec("soundfile")
    except (ImportError, ValueError):
        soundfile_spec = None
    if soundfile_spec is not None and soundfile_spec.origin:
        search_dirs.append(
            os.path.join(
                os.path.dirname(os.path.abspath(soundfile_spec.origin)),
                "_soundfile_data",
            )
        )

    try:
        data_spec = importlib.util.find_spec("_soundfile_data")
    except (ImportError, ValueError):
        data_spec = None
    if data_spec is not None:
        search_dirs.extend(data_spec.submodule_search_locations or [])

    meipass = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and meipass:
        search_dirs.append(os.path.join(meipass, "_soundfile_data"))

    seen = set()
    unique_dirs = []
    for directory in search_dirs:
        normalized = os.path.normcase(os.path.abspath(directory))
        if normalized not in seen:
            seen.add(normalized)
            unique_dirs.append(directory)

    system = platform.system()
    if system == "Darwin":
        names = (
            "libsndfile.dylib",
            "libsndfile_arm64.dylib",
            "libsndfile_x86_64.dylib",
        )
    elif system == "Windows":
        names = (
            "libsndfile64bit.dll",
            "libsndfile32bit.dll",
            "libsndfile_arm64.dll",
            "libsndfile_x64.dll",
            "libsndfile_x86.dll",
        )
    else:
        names = (
            "libsndfile.so.1",
            "libsndfile_x86_64.so",
            "libsndfile_arm64.so",
            "libsndfile_aarch64.so",
        )

    for directory in unique_dirs:
        for name in names:
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                yield path


def _patch_sndfile_lookup(library_path):
    """Make cffi's ``find_library('sndfile')`` resolve to ``library_path``.

    cffi calls ``ctypes.util.find_library`` when it loads a library by name.
    Patching only the ``sndfile`` name leaves every other lookup untouched and
    avoids changing the process-wide search behaviour.
    """
    global _sndfile_lookup_patched

    if _sndfile_lookup_patched:
        return

    original = ctypes.util.find_library

    def find_library(name):
        if name == "sndfile":
            return library_path
        return original(name)

    _sndfile_lookup_patched = True
    ctypes.util.find_library = find_library


def ensure_soundfile_library():
    """Ensure the legacy PySoundFile module can locate libsndfile.

    ``autosubsync`` depends on the abandoned ``PySoundFile`` distribution.
    Its platform-independent wheel omits libsndfile, and no architecture
    specific wheel exists for Apple Silicon, so importing ``soundfile`` raises
    ``OSError`` unless a system copy happens to be installed. When the
    maintained ``soundfile`` package provides a bundled library, redirect
    cffi's lookup to it. The function is a no-op when libsndfile already loads
    or no usable bundled copy is available.
    """
    global _soundfile_library_ready, _soundfile_library_handle

    if _soundfile_library_ready:
        return
    _soundfile_library_ready = True

    try:
        system_library = ctypes.util.find_library("sndfile")
    except Exception:
        system_library = None

    if system_library:
        try:
            _soundfile_library_handle = ctypes.CDLL(system_library)
            return
        except OSError as exc:
            logger.debug(
                "System libsndfile at %s could not be loaded: %s",
                system_library,
                exc,
            )

    for candidate in _soundfile_library_candidates():
        try:
            _soundfile_library_handle = ctypes.CDLL(candidate)
        except OSError as exc:
            logger.debug("Skipping unusable libsndfile %s: %s", candidate, exc)
            continue
        _patch_sndfile_lookup(candidate)
        logger.debug("Using bundled libsndfile at %s", candidate)
        return
