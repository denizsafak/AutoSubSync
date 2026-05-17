"""AutoSubSync command-line interface for autonomous pipelines.

Provides four subcommands: sync, shift, batch, config.

This module must remain free of PyQt6 Widgets/Gui imports at module load
time. The lightweight QtCore module may be loaded transitively (via
constants/utils for the QObject-based signals used elsewhere in the
codebase), but no display or event loop is started.
"""

# Path setup: the AutoSubSync codebase uses sibling-module imports (e.g.
# `from utils import ...`), so the `main/` directory must be on sys.path.
# This mirrors the setup that main/main.py performs for the GUI.
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

# Pre-import texts to satisfy the pre-existing utils <-> texts circular import.
# utils.py imports texts at module top, and texts module-load instantiates
# TranslationDict() which calls `from utils import get_locale`. If anything
# imports utils first, get_locale isn't defined yet and the import fails.
import texts  # noqa: F401,E402

import argparse  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402
import signal  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from typing import Optional  # noqa: E402

log = logging.getLogger("assy")


def _ensure_ffmpeg() -> None:
    """Make sure ffmpeg/ffprobe are reachable on PATH before invoking sync tools.

    Mirrors the GUI's behavior in main/main.py + utils.initialize_static_ffmpeg
    but Qt-free: in frozen builds the bundled FFMPEG_DIR is prepended; in pip
    installs the static_ffmpeg package's bundled (or auto-downloaded) binaries
    are added to PATH. Idempotent.
    """
    from constants import NEEDS_STATIC_FFMPEG, FFMPEG_DIR

    if FFMPEG_DIR and os.path.isdir(FFMPEG_DIR):
        if FFMPEG_DIR not in os.environ.get("PATH", "").split(os.pathsep):
            os.environ["PATH"] = (
                FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")
            )
        return

    if not NEEDS_STATIC_FFMPEG:
        return

    try:
        import static_ffmpeg
        from static_ffmpeg import run

        # Trigger download-on-demand if the binaries aren't cached yet.
        run.get_or_fetch_platform_executables_else_raise()
        static_ffmpeg.add_paths()
    except Exception as e:
        log.warning("Could not initialize static ffmpeg: %s", e)


SAVE_MODES_AUTO = (
    "save_next_to_input_subtitle",
    "overwrite_input_subtitle",
    "save_next_to_video",
    "save_next_to_video_with_same_filename",
    "save_to_desktop",
    "select_destination_folder",
)

TOOL_CHOICES = ("ffsubsync", "alass", "autosubsync")

EXIT_OK = 0
EXIT_SYNC_FAILED = 1
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130


def setup_logging(level_name: str, quiet: bool, verbose: bool, no_color: bool) -> None:
    """Initialize the root logger. CLI logs go to stderr; stdout is reserved
    for command output (paths in human mode, JSON objects in --json mode)."""
    if quiet:
        level = logging.WARNING
    elif verbose or level_name == "debug":
        level = logging.DEBUG
    else:
        level = getattr(logging, level_name.upper(), logging.INFO)

    handlers = []
    if not no_color:
        try:
            from rich.console import Console
            from rich.logging import RichHandler

            handlers = [
                RichHandler(
                    console=Console(file=sys.stderr, no_color=no_color),
                    show_path=False,
                    show_time=False,
                    rich_tracebacks=True,
                )
            ]
        except Exception:
            handlers = [logging.StreamHandler(sys.stderr)]
    else:
        handlers = [logging.StreamHandler(sys.stderr)]

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=handlers,
        force=True,
    )


def _config_path() -> str:
    from utils import get_user_config_path

    return get_user_config_path()


def _load_user_config(path: Optional[str]) -> dict:
    """Load the persisted user config (or an explicit file). Returns {} if absent."""
    if path:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    from utils import load_config

    return dict(load_config())


def _effective_config(args) -> dict:
    """Merge DEFAULT_OPTIONS with the user config. CLI overrides are applied
    by the per-subcommand handler."""
    from constants import DEFAULT_OPTIONS

    config = dict(DEFAULT_OPTIONS)
    config.update(_load_user_config(getattr(args, "config_file", None)))
    return config


def _apply_common_overrides(config: dict, args) -> None:
    """Apply CLI flags that override the persisted config for sync/batch."""
    if getattr(args, "tool", None):
        config["sync_tool"] = args.tool
    if getattr(args, "save_mode", None):
        config["automatic_save_location"] = args.save_mode
    if getattr(args, "save_folder", None):
        config["automatic_save_folder"] = args.save_folder
    if getattr(args, "encoding", None):
        config["output_subtitle_encoding"] = args.encoding
    if getattr(args, "prefix", False):
        config["add_tool_prefix"] = True
    elif getattr(args, "no_prefix", False):
        config["add_tool_prefix"] = False


def _validate_save_mode(config: dict) -> Optional[str]:
    """Return an error message if the save mode is incompatible with headless
    operation; None if OK."""
    if (
        config.get("automatic_save_location") == "select_destination_folder"
        and not config.get("automatic_save_folder")
    ):
        return (
            "--save-folder (or config key automatic_save_folder) is required "
            "when save-mode is select_destination_folder"
        )
    return None


def _build_callbacks(json_mode: bool, prefix: str = ""):
    """Construct SyncCallbacks bound to stderr logging.

    Subprocess overwrite-style lines (\\r-terminated) are only forwarded when
    stderr is a TTY; in pipelines they create noisy output.
    """
    from sync_core import SyncCallbacks

    interactive = sys.stderr.isatty()

    def on_log(msg, color):
        if not msg:
            return
        log.info("%s%s", prefix, msg)

    def on_progress(_percent):
        # Percent is also embedded in subprocess lines; the log already shows it.
        return

    def on_subprocess_line(line, is_overwrite):
        if not line:
            return
        if is_overwrite and not interactive:
            return
        if is_overwrite:
            sys.stderr.write("\r" + prefix + line + " " * 8)
            sys.stderr.flush()
        else:
            log.info("%s%s", prefix, line)

    def on_error(msg):
        log.error("%s%s", prefix, msg)

    return SyncCallbacks(
        on_log=on_log,
        on_progress=on_progress,
        on_subprocess_line=on_subprocess_line,
        on_error=on_error,
    )


def _apply_output_encoding(input_subtitle: str, output_path: str, config: dict) -> None:
    """Re-encode the output subtitle to match the configured target encoding."""
    enc = config.get("output_subtitle_encoding", "same_as_input")
    if enc == "disabled":
        return
    from utils import match_subtitle_encoding

    try:
        if enc == "same_as_input":
            match_subtitle_encoding(input_subtitle, output_path, None)
        else:
            match_subtitle_encoding(input_subtitle, output_path, None, enc)
    except Exception as e:
        log.warning("Failed to match subtitle encoding: %s", e)


def _emit_json(obj) -> None:
    json.dump(obj, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()


def cmd_sync(args) -> int:
    from sync_core import run_sync

    config = _effective_config(args)
    _apply_common_overrides(config, args)
    err = _validate_save_mode(config)
    if err:
        log.error(err)
        return EXIT_USAGE

    if not os.path.exists(args.video):
        log.error("Reference not found: %s", args.video)
        return EXIT_USAGE
    if not os.path.exists(args.subtitle):
        log.error("Subtitle not found: %s", args.subtitle)
        return EXIT_USAGE

    _ensure_ffmpeg()
    tool = config.get("sync_tool", "ffsubsync")
    callbacks = _build_callbacks(args.json)
    result = run_sync(
        args.video,
        args.subtitle,
        tool=tool,
        output=args.output,
        config=config,
        callbacks=callbacks,
    )
    if result.ok and result.output_path:
        _apply_output_encoding(args.subtitle, result.output_path, config)

    if args.json:
        _emit_json(
            {
                "ok": result.ok,
                "input": args.subtitle,
                "reference": args.video,
                "output": result.output_path,
                "tool": result.tool_used,
                "message": result.message,
                "returncode": result.returncode,
                "elapsed_ms": result.elapsed_ms,
                "cancelled": result.cancelled,
            }
        )
    else:
        if result.ok:
            log.info("Synced -> %s (%dms)", result.output_path, result.elapsed_ms)
        else:
            log.error("Sync failed: %s", result.message)

    return EXIT_OK if result.ok else EXIT_SYNC_FAILED


def cmd_shift(args) -> int:
    from sync_manual import shift_subtitle

    if not os.path.exists(args.subtitle):
        log.error("Subtitle not found: %s", args.subtitle)
        return EXIT_USAGE

    start = time.monotonic()
    output_path, ok, message = shift_subtitle(
        args.subtitle, args.milliseconds, args.output
    )
    elapsed_ms = int((time.monotonic() - start) * 1000)

    if args.json:
        _emit_json(
            {
                "ok": ok,
                "input": args.subtitle,
                "output": output_path,
                "milliseconds": args.milliseconds,
                "message": message,
                "elapsed_ms": elapsed_ms,
            }
        )
    else:
        if ok:
            log.info("Shifted %dms -> %s", args.milliseconds, output_path)
        else:
            log.error("Shift failed: %s", message)

    return EXIT_OK if ok else EXIT_SYNC_FAILED


def cmd_batch(args) -> int:
    from sync_core import run_sync
    from pairing import pair_paths, pair_folder, pair_folders
    from constants import SUBTITLE_EXTENSIONS

    if args.video_dir or args.subtitle_dir:
        if not (args.video_dir and args.subtitle_dir):
            log.error("--video-dir and --subtitle-dir must be provided together")
            return EXIT_USAGE
        pairs = pair_folders(args.video_dir, args.subtitle_dir, recursive=args.recursive)
    elif args.folder:
        pairs = pair_folder(args.folder, recursive=args.recursive)
    elif args.pair:
        for v, s in args.pair:
            if not os.path.exists(v):
                log.error("Reference not found: %s", v)
                return EXIT_USAGE
            if not os.path.exists(s):
                log.error("Subtitle not found: %s", s)
                return EXIT_USAGE
        pairs = [(v, s) for v, s in args.pair]
    else:
        log.error("batch needs --folder, --video-dir+--subtitle-dir, or --pair")
        return EXIT_USAGE

    if not pairs:
        log.warning("No video+subtitle pairs found")
        if args.json:
            _emit_json({"summary": {"total": 0, "ok": 0, "failed": 0, "skipped": 0}})
        return EXIT_OK

    config = _effective_config(args)
    _apply_common_overrides(config, args)
    if args.output_dir:
        # Overriding to a destination folder; create it if needed so
        # determine_output_path's isdir() check passes.
        os.makedirs(args.output_dir, exist_ok=True)
        config["automatic_save_location"] = "select_destination_folder"
        config["automatic_save_folder"] = args.output_dir
    err = _validate_save_mode(config)
    if err:
        log.error(err)
        return EXIT_USAGE

    skip = (
        args.skip_processed
        if args.skip_processed is not None
        else config.get("skip_previously_processed_videos", True)
    )
    mark = args.mark_processed if args.mark_processed is not None else skip

    processed_mgr = None
    if skip or mark:
        try:
            from processed_items_manager import get_processed_items_manager

            processed_mgr = get_processed_items_manager()
        except Exception as e:
            log.warning("Sync-tracking DB unavailable: %s", e)

    _ensure_ffmpeg()
    total = len(pairs)
    ok_count = 0
    fail_count = 0
    skip_count = 0
    failed_pairs = []

    for idx, (video, subtitle) in enumerate(pairs, 1):
        if skip and processed_mgr is not None:
            ext = os.path.splitext(video)[1].lower()
            if ext not in SUBTITLE_EXTENSIONS:
                try:
                    if processed_mgr.is_processed(video):
                        skip_count += 1
                        log.info(
                            "[%d/%d] skip (already processed): %s", idx, total, video
                        )
                        if args.json:
                            _emit_json(
                                {
                                    "ok": True,
                                    "skipped": True,
                                    "input": subtitle,
                                    "reference": video,
                                    "output": None,
                                    "message": "previously processed",
                                }
                            )
                        continue
                except Exception as e:
                    log.warning("is_processed check failed for %s: %s", video, e)

        callbacks = _build_callbacks(args.json, prefix=f"[{idx}/{total}] ")
        log.info("[%d/%d] %s + %s", idx, total, video, subtitle)
        tool = config.get("sync_tool", "ffsubsync")
        result = run_sync(
            video,
            subtitle,
            tool=tool,
            output=None,
            config=config,
            callbacks=callbacks,
        )
        if result.ok and result.output_path:
            _apply_output_encoding(subtitle, result.output_path, config)
            if mark and processed_mgr is not None:
                ext = os.path.splitext(video)[1].lower()
                if ext not in SUBTITLE_EXTENSIONS:
                    try:
                        processed_mgr.mark_as_processed(video, silent=True)
                    except Exception as e:
                        log.warning("mark_as_processed failed: %s", e)

        if args.json:
            _emit_json(
                {
                    "ok": result.ok,
                    "skipped": False,
                    "input": subtitle,
                    "reference": video,
                    "output": result.output_path,
                    "tool": result.tool_used,
                    "message": result.message,
                    "returncode": result.returncode,
                    "elapsed_ms": result.elapsed_ms,
                }
            )

        if result.ok:
            ok_count += 1
        else:
            fail_count += 1
            failed_pairs.append((video, subtitle, result.message))
            if not args.continue_on_error:
                log.error("Aborting batch on first failure (use --continue-on-error)")
                if args.json:
                    _emit_json(
                        {
                            "summary": {
                                "total": total,
                                "ok": ok_count,
                                "failed": fail_count,
                                "skipped": skip_count,
                                "aborted": True,
                            }
                        }
                    )
                return EXIT_SYNC_FAILED

    if args.json:
        _emit_json(
            {
                "summary": {
                    "total": total,
                    "ok": ok_count,
                    "failed": fail_count,
                    "skipped": skip_count,
                }
            }
        )
    log.info(
        "Batch complete: %d/%d ok, %d failed, %d skipped",
        ok_count,
        total,
        fail_count,
        skip_count,
    )
    return EXIT_OK if fail_count == 0 else EXIT_SYNC_FAILED


def _parse_config_value(value: str):
    """Best-effort conversion: booleans, ints, floats, JSON, else string."""
    low = value.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    try:
        return json.loads(value)
    except (ValueError, json.JSONDecodeError):
        pass
    return value


def cmd_config(args) -> int:
    from constants import DEFAULT_OPTIONS

    path = args.config_file or _config_path()

    if args.config_op == "path":
        print(path)
        return EXIT_OK

    if args.config_op == "list":
        config = _effective_config(args)
        for k in sorted(config.keys()):
            print(f"{k} = {config[k]!r}")
        return EXIT_OK

    if args.config_op == "get":
        config = _effective_config(args)
        if args.key not in config:
            log.error("Unknown config key: %s", args.key)
            return EXIT_USAGE
        v = config[args.key]
        if isinstance(v, (dict, list)):
            print(json.dumps(v, ensure_ascii=False))
        else:
            print(v)
        return EXIT_OK

    if args.config_op in ("set", "unset"):
        data = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    log.warning("Config file is invalid JSON; starting fresh")
                    data = {}
        if args.config_op == "set":
            if args.key not in DEFAULT_OPTIONS and not args.force:
                log.error(
                    "Unknown config key: %s (use --force to set anyway)", args.key
                )
                return EXIT_USAGE
            data[args.key] = _parse_config_value(args.value)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            log.info("Set %s = %r in %s", args.key, data[args.key], path)
        else:  # unset
            data.pop(args.key, None)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            log.info("Unset %s in %s", args.key, path)
        # Invalidate the cached config so subsequent calls in this process
        # see the change.
        try:
            import utils

            with utils._config_cache_lock:
                utils._config_cache = None
        except Exception:
            pass
        return EXIT_OK

    log.error("Unknown config op: %s", args.config_op)
    return EXIT_USAGE


def cmd_version(args) -> int:
    from constants import VERSION

    print(VERSION)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="assy-cli",
        description=(
            "AutoSubSync command-line interface for autonomous subtitle "
            "synchronization. Designed for use in pipelines and Docker."
        ),
    )
    p.add_argument(
        "--config-file",
        help="Path to a JSON config file (defaults to the user config)",
    )
    p.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging verbosity (default: info)",
    )
    p.add_argument("-q", "--quiet", action="store_true", help="Suppress info logs")
    p.add_argument("-v", "--verbose", action="store_true", help="Enable debug logs")
    p.add_argument("--no-color", action="store_true", help="Disable colored output")
    sub = p.add_subparsers(dest="subcommand")

    # sync
    s = sub.add_parser(
        "sync", help="Auto-sync one subtitle to a video or reference subtitle"
    )
    s.add_argument("video", help="Video or reference subtitle path")
    s.add_argument("subtitle", help="Subtitle file to sync")
    s.add_argument("-o", "--output", help="Output subtitle path (overrides save-mode)")
    s.add_argument("-t", "--tool", choices=TOOL_CHOICES, help="Sync engine")
    s.add_argument(
        "--save-mode",
        choices=SAVE_MODES_AUTO,
        help="Where to write the synced subtitle (when -o is not given)",
    )
    s.add_argument(
        "--save-folder",
        help="Destination folder when --save-mode=select_destination_folder",
    )
    s.add_argument(
        "--encoding",
        help='Output encoding (utf_8, latin_1, ..., "same_as_input", or "disabled")',
    )
    g = s.add_mutually_exclusive_group()
    g.add_argument(
        "--prefix",
        action="store_true",
        help="Prefix the output filename with the tool name",
    )
    g.add_argument(
        "--no-prefix",
        action="store_true",
        help="Do not prefix the output filename with the tool name",
    )
    s.add_argument("--json", action="store_true", help="Emit JSON result on stdout")
    s.set_defaults(handler=cmd_sync)

    # shift
    sh = sub.add_parser("shift", help="Shift subtitle timing by milliseconds")
    sh.add_argument("subtitle", help="Subtitle file to shift")
    sh.add_argument(
        "milliseconds",
        type=int,
        help="Shift in ms (positive = delay, negative = advance)",
    )
    sh.add_argument("-o", "--output", help="Output subtitle path")
    sh.add_argument("--json", action="store_true", help="Emit JSON result on stdout")
    sh.set_defaults(handler=cmd_shift)

    # batch
    b = sub.add_parser("batch", help="Batch sync many video+subtitle pairs")
    group = b.add_mutually_exclusive_group()
    group.add_argument(
        "--folder", help="One folder with both video and subtitle files"
    )
    b.add_argument(
        "--video-dir", help="Directory of video files (use with --subtitle-dir)"
    )
    b.add_argument(
        "--subtitle-dir", help="Directory of subtitle files (use with --video-dir)"
    )
    b.add_argument(
        "--pair",
        nargs=2,
        metavar=("VIDEO", "SUBTITLE"),
        action="append",
        help="Explicit pair (may be repeated)",
    )
    b.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories when scanning folders",
    )
    b.add_argument(
        "-o",
        "--output-dir",
        help="Write all synced subtitles to this directory",
    )
    b.add_argument("-t", "--tool", choices=TOOL_CHOICES, help="Sync engine")
    b.add_argument(
        "--save-mode",
        choices=SAVE_MODES_AUTO,
        help="Where to write each synced subtitle",
    )
    b.add_argument(
        "--save-folder",
        help="Destination folder when --save-mode=select_destination_folder",
    )
    b.add_argument("--encoding", help="Output encoding")
    g = b.add_mutually_exclusive_group()
    g.add_argument("--prefix", action="store_true")
    g.add_argument("--no-prefix", action="store_true")
    skip_g = b.add_mutually_exclusive_group()
    skip_g.add_argument(
        "--skip-processed",
        dest="skip_processed",
        action="store_const",
        const=True,
        default=None,
        help="Skip videos previously marked as processed",
    )
    skip_g.add_argument(
        "--no-skip-processed",
        dest="skip_processed",
        action="store_const",
        const=False,
        help="Process every pair regardless of history",
    )
    mark_g = b.add_mutually_exclusive_group()
    mark_g.add_argument(
        "--mark-processed",
        dest="mark_processed",
        action="store_const",
        const=True,
        default=None,
        help="Record successful syncs in the processed-items DB",
    )
    mark_g.add_argument(
        "--no-mark-processed",
        dest="mark_processed",
        action="store_const",
        const=False,
        help="Don't record successful syncs in the processed-items DB",
    )
    b.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Keep going after individual sync failures",
    )
    b.add_argument(
        "--json",
        action="store_true",
        help="Emit one JSON line per pair plus a summary line",
    )
    b.set_defaults(handler=cmd_batch)

    # config
    c = sub.add_parser("config", help="Manage the persistent user config")
    csub = c.add_subparsers(dest="config_op")
    csub.add_parser("path", help="Print the config file path")
    csub.add_parser("list", help="Print all effective config keys + values")
    cg = csub.add_parser("get", help="Print the value of one key")
    cg.add_argument("key")
    cs = csub.add_parser("set", help="Persist a key/value to the user config")
    cs.add_argument("key")
    cs.add_argument("value")
    cs.add_argument(
        "--force",
        action="store_true",
        help="Allow setting keys not in DEFAULT_OPTIONS",
    )
    cu = csub.add_parser("unset", help="Remove a key from the user config")
    cu.add_argument("key")
    c.set_defaults(handler=cmd_config)

    # version
    v = sub.add_parser("version", help="Print AutoSubSync version")
    v.set_defaults(handler=cmd_version)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.log_level, args.quiet, args.verbose, args.no_color)

    if not getattr(args, "subcommand", None):
        parser.print_help(sys.stderr)
        return EXIT_USAGE
    if args.subcommand == "config" and not getattr(args, "config_op", None):
        # argparse subsubparsers don't enforce required=True by default
        parser.parse_args(["config", "--help"])
        return EXIT_USAGE

    # Map SIGINT to a clean exit code
    def _sigint(_signum, _frame):
        raise KeyboardInterrupt()

    try:
        signal.signal(signal.SIGINT, _sigint)
    except Exception:
        pass

    try:
        return args.handler(args)
    except KeyboardInterrupt:
        log.error("Interrupted")
        return EXIT_INTERRUPTED
    except Exception as e:
        log.exception("Unexpected error: %s", e)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
