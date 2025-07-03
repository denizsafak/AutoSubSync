import sys
from multiprocessing import freeze_support
from ffsubsync.ffsubsync import main


def cli_entry(args=None):
    """
    Entry point for module-based execution. Accepts a list of arguments (excluding script name),
    sets sys.argv accordingly, and calls main().
    Returns the exit code from main()..
    """
    import sys as _sys

    old_argv = _sys.argv
    if args is not None:
        _sys.argv = [old_argv[0]] + args
    try:
        return main()
    finally:
        _sys.argv = old_argv


if __name__ == "__main__":
    freeze_support()  # fix https://github.com/pyinstaller/pyinstaller/issues/4104
    sys.exit(main())
