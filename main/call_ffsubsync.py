import os
import sys
from multiprocessing import freeze_support
from ffsubsync.constants import SUBSYNC_RESOURCES_ENV_MAGIC
from ffsubsync.ffsubsync import main

if SUBSYNC_RESOURCES_ENV_MAGIC not in os.environ:
    os.environ[SUBSYNC_RESOURCES_ENV_MAGIC] = getattr(sys, "_MEIPASS", "")

if __name__ == "__main__":
    freeze_support() # fix https://github.com/pyinstaller/pyinstaller/issues/4104
    # Pass command-line arguments (excluding script name) to main if possible
    # ffsubsync.main() expects sys.argv to be set, so just call main()
    sys.exit(main())
