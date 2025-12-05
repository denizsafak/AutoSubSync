import sys
import platform
import runpy, os, threading
import logging
from multiprocessing import freeze_support
from utils import get_resource_path

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

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


def _redirect_fd(fd, target_stream):
    orig_fd = os.dup(fd)
    r, w = os.pipe()
    os.dup2(w, fd)
    os.close(w)

    def reader():
        with os.fdopen(r, "r", encoding="utf-8", errors="replace") as pipe:
            for line in iter(pipe.readline, ""):
                print(line, end="", file=target_stream)

    t = threading.Thread(target=reader)
    t.daemon = True
    t.start()
    return orig_fd, t


def cli_entry(args=None):
    _argv = sys.argv
    model_file_default = get_resource_path(
        "autosubsync.resources.autosubsync", "trained-model.bin"
    )
    if args is None:
        args = sys.argv[1:]
    if "--model_file" not in args:
        args = ["--model_file", model_file_default] + args
    sys.argv = [_argv[0]] + args
    try:
        out = args[3]
        code = 0
        orig_stdout_fd, t_out = _redirect_fd(1, sys.stdout)
        orig_stderr_fd, t_err = _redirect_fd(2, sys.stderr)
        try:
            sys.modules.pop("autosubsync.main", None)
            runpy.run_module("autosubsync.main", run_name="__main__")
        except SystemExit as e:
            code = e.code if hasattr(e, "code") else 1
        except Exception as ex:
            code = 1
            logger.exception(ex)
        finally:
            os.dup2(orig_stdout_fd, 1)
            os.dup2(orig_stderr_fd, 2)
            os.close(orig_stdout_fd)
            os.close(orig_stderr_fd)
            t_out.join()
            t_err.join()
            sys.argv = _argv
        return 0 if out and os.path.exists(out) else code
    finally:
        sys.argv = _argv


if __name__ == "__main__":
    freeze_support()
    sys.exit(cli_entry())
