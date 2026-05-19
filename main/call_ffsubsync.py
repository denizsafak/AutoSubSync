import sys
import platform
from multiprocessing import freeze_support
import compat  # Shim for pkg_resources (removed in Python 3.14+)

# Monkey-patch subprocess.Popen to always use CREATE_NO_WINDOW on Windows
import subprocess

if platform.system() == "Windows":
    _orig_popen = subprocess.Popen

    def _patched_popen(*args, **kwargs):
        flags = kwargs.get("creationflags", 0)
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        kwargs["creationflags"] = flags
        return _orig_popen(*args, **kwargs)

    subprocess.Popen = _patched_popen


def _load_ffsubsync():
    try:
        from ffsubsync.ffsubsync import main as ffsubsync_main
        return ffsubsync_main, None
    except Exception as e:
        return None, e


def cli_entry(args=None):
    """
    Entry point for module-based execution. Accepts a list of arguments (excluding script name),
    sets sys.argv accordingly, and calls main().
    Returns the exit code from main()..
    """
    import sys as _sys

    ffsubsync_main, import_error = _load_ffsubsync()
    if ffsubsync_main is None:
        msg = (
            "ffsubsync is not available. Install it with 'pip install ffsubsync' "
            "or 'pip install assy' to use this sync tool."
        )
        print(msg, file=_sys.stderr)
        if import_error:
            print(f"Import error: {import_error}", file=_sys.stderr)
        return 1

    old_argv = _sys.argv
    if args is not None:
        _sys.argv = [old_argv[0]] + args
    try:
        return ffsubsync_main()
    finally:
        _sys.argv = old_argv


if __name__ == "__main__":
    freeze_support()  # fix https://github.com/pyinstaller/pyinstaller/issues/4104
    sys.exit(cli_entry())
