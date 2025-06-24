#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from shlex import split
import json
import math
from multiprocessing import freeze_support
import logging

from ffsubsync.constants import SUBSYNC_RESOURCES_ENV_MAGIC
from ffsubsync.ffsubsync import main, run, make_parser

if SUBSYNC_RESOURCES_ENV_MAGIC not in os.environ:
    os.environ[SUBSYNC_RESOURCES_ENV_MAGIC] = getattr(sys, "_MEIPASS", "")

command_queue = []

logging.basicConfig(level=logging.INFO, format='[SERVER] %(message)s')

def output(data):
    logging.info(json.dumps(data, ensure_ascii=False))

def add_command(command: str):
    command_queue.append(command)
    output({"status": "added"})

def execute(command: str):
    parser = make_parser()
    args = parser.parse_args(split(command))
    try:
        result = run(args)["retval"]
        logging.info("")
        if result == 0:
            logging.info('[OK] Subtitle synchronization completed successfully.')
            output({ "status": "done", "command": command })
        else:
            logging.error('[FAIL] Subtitle synchronization failed.')
            output({ "status": "fail", "command": command, "error": "Subtitle synchronization failed." })
        logging.info("")
    except Exception as e:
        logging.error('[FAIL] Execution failed: %s', str(e), exc_info=True)
        output({ "status": "fail", "command": command, "error": str(e) })

def start_tasks():
    i = 0
    total = len(command_queue)
    while command_queue:
        command = command_queue.pop(0)
        try:
            output({ "status": "running", "command": command, "percent": math.floor((i / total) * 100) })
            execute(command)
        except Exception as e:
            logging.error('[FAIL] Task execution failed: %s', str(e), exc_info=True)
            output({ "status": "fail", "message": str(e), "command": command, "error": str(e) })
        i += 1
    output({ "status": "ready" })

if __name__ == "__main__":
    freeze_support() # fix https://github.com/pyinstaller/pyinstaller/issues/4104
    sys.exit(main())