"""Linux packaging helpers for AutoSubSync.

The module turns the standalone PyInstaller bundle in ``dist/AutoSubSync``
into a Debian ``.deb`` package without requiring Debian-only build tools.
It also owns the freedesktop.org desktop entry shared by the AppImage and
the ``.deb`` so both packages expose identical launcher metadata.

The generated package follows the usual Debian binary-package layout:

* ``/opt/autosubsync`` holds the self-contained application bundle,
* ``/usr/bin/autosubsync`` is a relative symlink to the GUI executable,
* ``/usr/share/applications`` and ``/usr/share/icons`` hold desktop metadata,
* ``/usr/share/doc/autosubsync`` holds the copyright file,
* the control archive holds the control file, checksums and maintainer
  scripts.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import os
import platform
import re
import shutil
import tarfile
import tempfile
import time

# =============================================================================
# Debian Package Metadata
# =============================================================================

PACKAGE_NAME = "autosubsync"
PACKAGE_REVISION = "1"
MAINTAINER = "Deniz Şafak <denizsafak98@gmail.com>"
HOMEPAGE = "https://github.com/denizsafak/AutoSubSync"
SECTION = "video"
PRIORITY = "optional"
INSTALL_ROOT = "opt/autosubsync"
BINARY_NAME = "AutoSubSync"
COMMAND_NAME = "autosubsync"

# Desktop file name must match QGuiApplication.setDesktopFileName() in
# main/main.py so Wayland compositors can associate the window with its
# launcher icon.
DESKTOP_FILE_NAME = "autosubsyncapp.desktop"

# Runtime libraries the Linux bundle links against but does not ship.
# PyInstaller bundles almost everything else (Qt, glib, GTK, libstdc++...),
# so this list only contains the base system libraries. The test workflow
# verifies it by running ``ldd`` against the installed executable.
BASE_DEPENDS = (
    "libc6",
    "libdrm2",
    "libegl1",
    "libgl1",
    "libwayland-client0",
    "libwayland-egl1",
    "libxcb1",
    "zlib1g",
)
RECOMMENDS = ("fonts-dejavu-core", "xdg-utils")

DESCRIPTION_SYNOPSIS = "automatic subtitle synchronization tool"
DESCRIPTION_BODY = (
    "AutoSubSync is a user-friendly tool that automatically synchronizes",
    "subtitle files with videos or audio files. It supports ffsubsync,",
    "autosubsync, alass, and LAPSE, common subtitle formats, and both",
    "automatic and manual timing adjustments from a graphical interface.",
)

# Compress the tar members once; gzip is supported by every dpkg release
# that ships on the distributions this package targets.
_TAR_COMPRESS_LEVEL = 6

# Locale-independent names for the RFC 2822 date in the Debian changelog.
_CHANGELOG_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_CHANGELOG_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


# =============================================================================
# Small Helpers
# =============================================================================


def _build_timestamp() -> int:
    """Return one archive timestamp for all entries.

    ``SOURCE_DATE_EPOCH`` is honoured so reproducible-build systems can
    produce byte-identical packages; otherwise the current time is used.
    """
    value = os.environ.get("SOURCE_DATE_EPOCH", "")
    if value.isdigit():
        return int(value)
    return int(time.time())


def _minimum_libc_version() -> str | None:
    """Return the glibc ``major.minor`` the build host linked against.

    Debian dependency fields accept a version floor, and PyInstaller embeds
    the interpreter and shared libraries from the build host. Recording the
    floor prevents installing a package whose bundled libraries need a newer
    glibc than the target distribution provides. ``None`` means the check is
    not applicable (for example on a musl host).
    """
    libc_name, libc_version = platform.libc_ver()
    parts = libc_version.split(".")
    if (
        libc_name == "glibc"
        and len(parts) >= 2
        and all(part.isdigit() for part in parts[:2])
    ):
        return ".".join(parts[:2])
    return None


def _dependency_field() -> str:
    """Build the ``Depends`` value, adding an optional glibc version floor."""
    dependencies: list[str] = list(BASE_DEPENDS)
    libc_version = _minimum_libc_version()
    if libc_version:
        dependencies[0] = f"libc6 (>= {libc_version})"
    return ", ".join(dependencies)


def _iter_stage(root: str):
    """Yield ``(posix_relpath, absolute_path, kind)`` for a staged tree.

    Entries are sorted at every directory level so consecutive builds emit
    identical archives. Symlinks are reported as links and are never
    followed, which keeps user-controlled trees from escaping ``root``.
    """
    root = os.path.abspath(root)

    def walk(directory: str):
        """Recursively yield entries below ``directory`` in sorted order."""
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
            for entry in entries:
                relpath = os.path.relpath(entry.path, root).replace(os.sep, "/")
                if entry.is_symlink():
                    yield relpath, entry.path, "symlink"
                elif entry.is_dir(follow_symlinks=False):
                    yield relpath, entry.path, "dir"
                    yield from walk(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    yield relpath, entry.path, "file"

    yield from walk(root)


def _installed_size(stage: str) -> int:
    """Return the Debian ``Installed-Size`` field value in KiB."""
    total_bytes = sum(
        os.path.getsize(abspath)
        for _, abspath, kind in _iter_stage(stage)
        if kind == "file"
    )
    return (total_bytes + 1023) // 1024


def _md5sums(stage: str) -> str:
    """Build the ``md5sums`` control member for the staged regular files.

    Debian uses this file for integrity verification and package auditing;
    symlinks and directories are intentionally excluded.
    """
    lines = []
    for relpath, abspath, kind in _iter_stage(stage):
        if kind != "file":
            continue
        try:
            digest = hashlib.md5(usedforsecurity=False)
        except TypeError:  # Python implementations without the keyword
            digest = hashlib.md5()
        with open(abspath, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        lines.append(f"{digest.hexdigest()}  {relpath}\n")
    return "".join(lines)


# =============================================================================
# Package Metadata Builders
# =============================================================================


def normalize_version(version: str) -> str:
    """Return a Debian-compatible upstream version string.

    Debian versions must start with a digit and may only contain ASCII
    alphanumerics plus ``.``, ``+``, ``-`` and ``~``. A leading ``v`` is
    stripped because ``main/VERSION`` may contain one, and any other invalid
    character is replaced with ``-`` rather than producing an unusable
    package.

    Raises:
        ValueError: When no usable version remains.
    """
    cleaned = version.strip()
    if cleaned[:1].lower() == "v":
        cleaned = cleaned[1:]
    cleaned = "".join(
        character
        if character.isascii() and (character.isalnum() or character in ".+-~")
        else "-"
        for character in cleaned
    )
    if not cleaned:
        raise ValueError("Cannot build a Debian package without a version")
    if not cleaned[0].isdigit():
        cleaned = f"0~{cleaned}"
    return cleaned


def build_desktop_entry(
    exec_command: str,
    version: str | None = None,
    *,
    appimage: bool = False,
) -> str:
    """Build the freedesktop.org desktop entry used by Linux packages.

    Args:
        exec_command: Executable as desktop environments should launch it.
        version: Application version for ``X-AppImage-Version``.
        appimage: Add AppImage-specific metadata when true.

    Returns:
        A complete desktop entry ending with a newline.
    """
    lines = [
        "[Desktop Entry]",
        "Version=1.0",
        "Name=AutoSubSync",
        "GenericName=Automatic Subtitle Synchronizer",
        f"Exec={exec_command} %f",
        "Icon=autosubsync",
        "Type=Application",
        "Categories=AudioVideo;Video;",
        "Comment=Automatic subtitle synchronization tool.",
        "Terminal=false",
        "StartupWMClass=AutoSubSync",
    ]
    if appimage and version:
        lines.append(f"X-AppImage-Version={version}")
    return "\n".join(lines) + "\n"


def read_png_dimensions(path: str) -> tuple[int, int] | None:
    """Read width and height from a PNG ``IHDR`` chunk.

    Returns ``None`` when the file is missing, unreadable, or not a PNG so
    the caller can fall back to a generic icon location instead of failing
    the whole build.
    """
    try:
        with open(path, "rb") as handle:
            header = handle.read(24)
    except OSError:
        return None
    if (
        len(header) < 24
        or header[:8] != b"\x89PNG\r\n\x1a\n"
        or header[12:16] != b"IHDR"
    ):
        return None
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    return (width, height) if width and height else None


def _build_control_file(
    version: str,
    architecture: str,
    installed_size: int,
    depends: str,
) -> str:
    """Build the binary package ``DEBIAN/control`` content."""
    description = "\n".join(f" {line}" if line else " ." for line in DESCRIPTION_BODY)
    return (
        f"Package: {PACKAGE_NAME}\n"
        f"Version: {version}\n"
        f"Section: {SECTION}\n"
        f"Priority: {PRIORITY}\n"
        f"Architecture: {architecture}\n"
        f"Maintainer: {MAINTAINER}\n"
        f"Installed-Size: {installed_size}\n"
        f"Depends: {depends}\n"
        f"Recommends: {', '.join(RECOMMENDS)}\n"
        f"Homepage: {HOMEPAGE}\n"
        f"Description: {DESCRIPTION_SYNOPSIS}\n"
        f"{description}\n"
    )


def _build_maintainer_script(actions: tuple[str, ...]) -> str:
    """Build an idempotent maintainer script that refreshes desktop caches.

    Args:
        actions: dpkg actions for which the caches should be refreshed,
            for example ``("configure",)`` for ``postinst``.
    """
    patterns = "|".join(actions)
    return f"""#!/bin/sh
set -e

case "$1" in
    {patterns})
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database -q /usr/share/applications || true
        fi

        if command -v gtk-update-icon-cache >/dev/null 2>&1; then
            gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
        fi
        ;;
esac

exit 0
"""


def _build_changelog(version: str, mtime: int) -> str:
    """Build a minimal, locale-independent Debian changelog entry.

    Args:
        version: Full Debian version including the packaging revision.
        mtime: Build timestamp used for the changelog date.
    """
    stamp = time.gmtime(mtime)
    date = (
        f"{_CHANGELOG_DAYS[stamp.tm_wday]}, {stamp.tm_mday:02d} "
        f"{_CHANGELOG_MONTHS[stamp.tm_mon - 1]} {stamp.tm_year} "
        f"{stamp.tm_hour:02d}:{stamp.tm_min:02d}:{stamp.tm_sec:02d} +0000"
    )
    upstream_version = version.rsplit("-", 1)[0]
    return (
        f"{PACKAGE_NAME} ({version}) unstable; urgency=medium\n"
        "\n"
        f"  * Package AutoSubSync {upstream_version} for Linux.\n"
        "\n"
        f" -- {MAINTAINER}  {date}\n"
    )


def _build_copyright_file() -> str:
    """Return the DEP-5 copyright file installed as package documentation."""
    return (
        "Format: https://www.debian.org/doc/packaging-manuals/"
        "copyright-format/1.0/\n"
        "Upstream-Name: AutoSubSync\n"
        f"Upstream-Contact: {MAINTAINER}\n"
        f"Source: {HOMEPAGE}\n"
        "\n"
        "Files: *\n"
        "Copyright: 2024-2026 Deniz Şafak\n"
        "License: GPL-3.0-or-later\n"
        " This program is free software: you can redistribute it and/or modify\n"
        " it under the terms of the GNU General Public License as published by\n"
        " the Free Software Foundation, either version 3 of the License, or\n"
        " (at your option) any later version.\n"
        " .\n"
        " This program is distributed in the hope that it will be useful,\n"
        " but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
        " MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the\n"
        " GNU General Public License for more details.\n"
        " .\n"
        " On Debian systems, the complete text of the GNU General Public\n"
        " License version 3 can be found in /usr/share/common-licenses/GPL-3.\n"
        "Comment: Bundled third-party components such as FFmpeg, Qt, Python\n"
        " packages, ALASS, and LAPSE retain their own upstream licenses.\n"
    )


# =============================================================================
# Tar and ar Writers
# =============================================================================


def _add_control_member(
    tar: tarfile.TarFile,
    name: str,
    data: bytes,
    mtime: int,
    mode: int = 0o644,
) -> None:
    """Add one in-memory member to an open control tar archive."""
    info = tarfile.TarInfo(f"./{name}")
    info.size = len(data)
    info.mode = mode
    info.mtime = mtime
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    tar.addfile(info, io.BytesIO(data))


def _add_staged_member(
    tar: tarfile.TarFile,
    relpath: str,
    abspath: str,
    kind: str,
    mtime: int,
) -> None:
    """Add one staged filesystem entry to an open data tar archive."""
    info = tarfile.TarInfo(f"./{relpath}")
    info.mtime = mtime
    info.uid = info.gid = 0
    info.uname = info.gname = "root"

    if kind == "dir":
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        tar.addfile(info)
    elif kind == "symlink":
        info.type = tarfile.SYMTYPE
        info.linkname = os.readlink(abspath)
        info.mode = 0o777
        tar.addfile(info)
    else:
        file_stat = os.stat(abspath, follow_symlinks=False)
        info.size = file_stat.st_size
        info.mode = 0o755 if file_stat.st_mode & 0o111 else 0o644
        with open(abspath, "rb") as handle:
            tar.addfile(info, handle)


def _write_control_tar(
    path: str,
    members: list[tuple[str, bytes, int]],
    mtime: int,
) -> None:
    """Write ``control.tar.gz`` with control data and maintainer scripts."""
    with open(path, "wb") as raw:
        with gzip.GzipFile(
            fileobj=raw,
            mode="wb",
            compresslevel=_TAR_COMPRESS_LEVEL,
            mtime=mtime,
        ) as compressed:
            with tarfile.open(
                fileobj=compressed,
                mode="w",
                format=tarfile.GNU_FORMAT,
            ) as tar:
                for name, data, mode in members:
                    _add_control_member(tar, name, data, mtime, mode)


def _write_data_tar(path: str, stage: str, mtime: int) -> None:
    """Write ``data.tar.gz`` from the complete staged filesystem tree."""
    with open(path, "wb") as raw:
        with gzip.GzipFile(
            fileobj=raw,
            mode="wb",
            compresslevel=_TAR_COMPRESS_LEVEL,
            mtime=mtime,
        ) as compressed:
            with tarfile.open(
                fileobj=compressed,
                mode="w",
                format=tarfile.GNU_FORMAT,
            ) as tar:
                for relpath, abspath, kind in _iter_stage(stage):
                    _add_staged_member(tar, relpath, abspath, kind, mtime)


def _write_ar_member(
    handle,
    name: str,
    size: int,
    mtime: int,
    source: str | None = None,
    data: bytes | None = None,
) -> None:
    """Write one ar member header, payload, and even-byte padding.

    ``dpkg`` reads plain space-padded member names and the ``100644`` mode
    used by ``dpkg-deb``; the payload is streamed from ``source`` for large
    members so the package is never held in memory.
    """
    if len(name.encode("ascii")) > 16:
        raise ValueError(f"ar member name is too long: {name!r}")
    header = f"{name:<16}{mtime:<12}{0:<6}{0:<6}{0o100644:<8o}{size:<10}`\n"
    handle.write(header.encode("ascii"))
    if data is not None:
        handle.write(data)
    elif source is not None:
        with open(source, "rb") as source_handle:
            shutil.copyfileobj(source_handle, handle, 1024 * 1024)
    if size % 2:
        handle.write(b"\n")


def _write_deb(
    output_path: str,
    control_tar: str,
    data_tar: str,
    mtime: int,
) -> None:
    """Assemble the final ``ar`` archive that dpkg and apt install."""
    with open(output_path, "wb") as handle:
        handle.write(b"!<arch>\n")
        _write_ar_member(handle, "debian-binary", 4, mtime, data=b"2.0\n")
        _write_ar_member(
            handle,
            "control.tar.gz",
            os.path.getsize(control_tar),
            mtime,
            source=control_tar,
        )
        _write_ar_member(
            handle,
            "data.tar.gz",
            os.path.getsize(data_tar),
            mtime,
            source=data_tar,
        )


# =============================================================================
# Public Entry Point
# =============================================================================


def build_deb(
    repo_root: str,
    version: str,
    architecture: str,
    output_dir: str | None = None,
) -> str:
    """Build a Debian package from the PyInstaller Linux bundle.

    Args:
        repo_root: Repository root containing ``dist/AutoSubSync`` and
            ``main/assets/icon.png``.
        version: Application version, normally read from ``main/VERSION``.
        architecture: Debian architecture name such as ``amd64`` or ``arm64``.
        output_dir: Destination directory; defaults to ``repo_root``.

    Returns:
        The absolute path to the generated ``.deb`` file.

    Raises:
        FileNotFoundError: The PyInstaller bundle or application icon is
            missing.
        ValueError: The version or architecture cannot be represented in a
            Debian package.
    """
    if not re.fullmatch(r"[a-z0-9]+", architecture):
        raise ValueError(f"Invalid Debian architecture: {architecture!r}")

    repo_root = os.path.abspath(repo_root)
    source_dir = os.path.join(repo_root, "dist", "AutoSubSync")
    executable = os.path.join(source_dir, BINARY_NAME)
    if not os.path.isdir(source_dir):
        raise FileNotFoundError(
            f"PyInstaller output not found: {source_dir}. "
            "Run build_with_pyinstaller() first."
        )
    if not os.path.isfile(executable):
        raise FileNotFoundError(f"Packaged executable not found: {executable}")

    icon_path = os.path.join(repo_root, "main", "assets", "icon.png")
    if not os.path.isfile(icon_path):
        raise FileNotFoundError(f"Application icon not found: {icon_path}")

    normalized_version = normalize_version(version)
    debian_version = f"{normalized_version}-{PACKAGE_REVISION}"
    output_dir = os.path.abspath(output_dir or repo_root)
    os.makedirs(output_dir, exist_ok=True)
    mtime = _build_timestamp()

    stage_root = os.path.join(repo_root, "dist", "deb")
    stage_dir = os.path.join(
        stage_root, f"{PACKAGE_NAME}_{normalized_version}_{architecture}"
    )
    if os.path.isdir(stage_dir):
        shutil.rmtree(stage_dir)
    os.makedirs(stage_dir)

    try:
        install_dir = os.path.join(stage_dir, *INSTALL_ROOT.split("/"))
        shutil.copytree(source_dir, install_dir, symlinks=True)
        os.chmod(os.path.join(install_dir, BINARY_NAME), 0o755)

        bin_dir = os.path.join(stage_dir, "usr", "bin")
        os.makedirs(bin_dir, exist_ok=True)
        os.symlink(
            os.path.join("..", "..", *INSTALL_ROOT.split("/"), BINARY_NAME),
            os.path.join(bin_dir, COMMAND_NAME),
        )

        desktop_dir = os.path.join(stage_dir, "usr", "share", "applications")
        os.makedirs(desktop_dir, exist_ok=True)
        with open(
            os.path.join(desktop_dir, DESKTOP_FILE_NAME),
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(build_desktop_entry(f"/usr/bin/{COMMAND_NAME}"))

        dimensions = read_png_dimensions(icon_path)
        if dimensions:
            icon_dir = os.path.join(
                stage_dir,
                "usr",
                "share",
                "icons",
                "hicolor",
                f"{dimensions[0]}x{dimensions[1]}",
                "apps",
            )
        else:
            icon_dir = os.path.join(stage_dir, "usr", "share", "pixmaps")
        os.makedirs(icon_dir, exist_ok=True)
        shutil.copy2(icon_path, os.path.join(icon_dir, f"{PACKAGE_NAME}.png"))

        doc_dir = os.path.join(stage_dir, "usr", "share", "doc", PACKAGE_NAME)
        os.makedirs(doc_dir, exist_ok=True)
        with open(
            os.path.join(doc_dir, "copyright"),
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(_build_copyright_file())

        with open(
            os.path.join(doc_dir, "changelog.Debian.gz"), "wb"
        ) as raw:
            with gzip.GzipFile(
                fileobj=raw, mode="wb", mtime=mtime
            ) as compressed:
                compressed.write(
                    _build_changelog(debian_version, mtime).encode("utf-8")
                )

        control_members = [
            (
                "control",
                _build_control_file(
                    debian_version,
                    architecture,
                    _installed_size(stage_dir),
                    _dependency_field(),
                ).encode("utf-8"),
                0o644,
            ),
            ("md5sums", _md5sums(stage_dir).encode("utf-8"), 0o644),
            (
                "postinst",
                _build_maintainer_script(("configure",)).encode("utf-8"),
                0o755,
            ),
            (
                "postrm",
                _build_maintainer_script(("remove", "purge")).encode("utf-8"),
                0o755,
            ),
        ]

        output_path = os.path.join(
            output_dir, f"AutoSubSync-linux-{architecture}.deb"
        )
        if os.path.exists(output_path):
            os.remove(output_path)
        partial_path = f"{output_path}.part"
        with tempfile.TemporaryDirectory(
            prefix=".autosubsync-deb-", dir=output_dir
        ) as temp_dir:
            control_tar = os.path.join(temp_dir, "control.tar.gz")
            data_tar = os.path.join(temp_dir, "data.tar.gz")
            try:
                _write_control_tar(control_tar, control_members, mtime)
                _write_data_tar(data_tar, stage_dir, mtime)
                _write_deb(partial_path, control_tar, data_tar, mtime)
                os.replace(partial_path, output_path)
            finally:
                if os.path.exists(partial_path):
                    os.remove(partial_path)

        print(f"Debian package created: {output_path}")
        print(
            "Package size: "
            f"{os.path.getsize(output_path) / (1024 * 1024):.1f} MB"
        )
        return output_path
    finally:
        shutil.rmtree(stage_dir, ignore_errors=True)
        if os.path.isdir(stage_root) and not os.listdir(stage_root):
            os.rmdir(stage_root)
