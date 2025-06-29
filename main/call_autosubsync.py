import sys
from multiprocessing import freeze_support
import runpy, os, importlib.util, site, threading
from utils import get_resource_path

AUTOSUBSYNC_MODEL = get_resource_path(
    "autosubsync.resources.autosubsync", "trained-model.bin"
)

def _redirect_fd(fd, target_stream):
    orig_fd = os.dup(fd)
    r, w = os.pipe()
    os.dup2(w, fd)
    os.close(w)
    def reader():
        with os.fdopen(r, 'r', encoding='utf-8', errors='replace') as pipe:
            for line in iter(pipe.readline, ''):
                print(line, end='', file=target_stream)
    t = threading.Thread(target=reader)
    t.daemon = True
    t.start()
    return orig_fd, t

def cli_entry(args=None):
    _argv = sys.argv
    if args: sys.argv = [_argv[0]] + args
    try:
        model_dir = os.path.dirname(AUTOSUBSYNC_MODEL) if AUTOSUBSYNC_MODEL and os.path.exists(AUTOSUBSYNC_MODEL) else None
        out = args[2] if args and len(args) > 2 else (sys.argv[3] if len(sys.argv) > 3 else None)
        code = 0
        orig_stdout_fd, t_out = _redirect_fd(1, sys.stdout)
        orig_stderr_fd, t_err = _redirect_fd(2, sys.stderr)
        try:
            if model_dir:
                cwd = os.getcwd(); os.chdir(model_dir)
                try:
                    sys.modules.pop('autosubsync.main', None)
                    runpy.run_module('autosubsync.main', run_name='__main__')
                finally:
                    os.chdir(cwd)
            else:
                sys.modules.pop('autosubsync.main', None)
                runpy.run_module('autosubsync.main', run_name='__main__')
        except SystemExit as e:
            code = e.code if hasattr(e, 'code') else 1
        except Exception:
            code = 1
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
