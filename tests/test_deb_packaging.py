"""Tests for the Debian package builder in ``linux_packaging``.

The tests build a package from a small fixture tree and inspect the resulting
ar/tar containers directly, so they also run on development machines without
``dpkg`` installed. The packaging logic is Linux-specific; the tests are
skipped on platforms where creating the /usr/bin symlink is not meaningful.
"""

import gzip
import io
import os
import shutil
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import linux_packaging


def _read_ar(path):
    """Return an ordered ``{member_name: bytes}`` mapping for an ar archive.

    Args:
        path: Path to the ``.deb`` file to parse.

    Returns:
        Member names mapped to their raw payload bytes, in archive order.

    Raises:
        AssertionError: The file is not an ar archive.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    if not data.startswith(b"!<arch>\n"):
        raise AssertionError("Not an ar archive")

    members = {}
    offset = 8
    while offset < len(data):
        header = data[offset : offset + 60]
        if len(header) < 60:
            break
        name = header[:16].decode("ascii").rstrip()
        size = int(header[48:58].decode("ascii").strip())
        offset += 60
        members[name] = data[offset : offset + size]
        offset += size + (size % 2)
    return members


def _read_tar(data):
    """Return ``{member_name: (TarInfo, payload_bytes)}`` for a tar archive.

    Args:
        data: Complete gzipped tar payload.

    Returns:
        Member names mapped to their metadata and file content.
    """
    members = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            handle = tar.extractfile(member)
            members[member.name] = (
                member,
                handle.read() if handle is not None else b"",
            )
    return members


class VersionTests(unittest.TestCase):
    """Version normalization must always produce a Debian-valid string."""

    def test_plain_version_is_preserved(self):
        """A normal numeric version passes through unchanged."""
        self.assertEqual(linux_packaging.normalize_version("6.6"), "6.6")

    def test_leading_v_is_stripped(self):
        """Release tags such as ``v6.7`` map to the numeric version."""
        self.assertEqual(linux_packaging.normalize_version("v6.7"), "6.7")

    def test_invalid_characters_are_replaced(self):
        """Spaces and unsupported characters become Debian separators."""
        self.assertEqual(
            linux_packaging.normalize_version("6.6 beta"), "6.6-beta"
        )

    def test_non_numeric_version_gets_epoch_prefix(self):
        """Debian versions must start with a digit, so one is prepended."""
        self.assertEqual(
            linux_packaging.normalize_version("unknown"), "0~unknown"
        )

    def test_empty_version_is_rejected(self):
        """An empty VERSION file is a packaging error, not a valid version."""
        with self.assertRaises(ValueError):
            linux_packaging.normalize_version("   ")


class DesktopEntryTests(unittest.TestCase):
    """The shared desktop entry must stay valid for both package formats."""

    def test_deb_entry_uses_installed_command(self):
        """The .deb launcher uses the stable /usr/bin command name."""
        entry = linux_packaging.build_desktop_entry("/usr/bin/autosubsync")
        self.assertIn("Exec=/usr/bin/autosubsync %f", entry)
        self.assertIn("Icon=autosubsync", entry)
        self.assertNotIn("X-AppImage-Version", entry)

    def test_appimage_entry_includes_version(self):
        """The AppImage entry records the application version."""
        entry = linux_packaging.build_desktop_entry(
            "AutoSubSync", version="6.6", appimage=True
        )
        self.assertIn("Exec=AutoSubSync %f", entry)
        self.assertIn("X-AppImage-Version=6.6", entry)


@unittest.skipIf(os.name == "nt", "symbolic links are not portable on Windows")
class PackageLayoutTests(unittest.TestCase):
    """Build a complete package from a fixture and inspect the containers."""

    def setUp(self):
        """Create a minimal repository tree with the real application icon."""
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.repo_root = os.path.join(self._temp_dir.name, "repo")

        bundle_dir = os.path.join(self.repo_root, "dist", "AutoSubSync")
        os.makedirs(bundle_dir)
        executable = os.path.join(bundle_dir, "AutoSubSync")
        with open(executable, "wb") as handle:
            handle.write(b"#!/bin/sh\nexit 0\n")
        os.chmod(executable, 0o755)

        assets_dir = os.path.join(self.repo_root, "main", "assets")
        os.makedirs(assets_dir)
        icon_source = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "main", "assets", "icon.png"
            )
        )
        shutil.copy2(icon_source, os.path.join(assets_dir, "icon.png"))

    def _build(self):
        """Build the fixture package and return its parsed containers."""
        output_dir = os.path.join(self._temp_dir.name, "out")
        deb_path = linux_packaging.build_deb(
            self.repo_root, "9.9", "amd64", output_dir
        )
        self.assertTrue(os.path.isfile(deb_path))
        ar_members = _read_ar(deb_path)
        return ar_members, _read_tar(ar_members["control.tar.gz"]), _read_tar(
            ar_members["data.tar.gz"]
        )

    def test_archive_members_and_control_metadata(self):
        """The package has the mandatory ar members and control fields."""
        ar_members, control, _ = self._build()

        self.assertEqual(
            list(ar_members), ["debian-binary", "control.tar.gz", "data.tar.gz"]
        )
        self.assertEqual(ar_members["debian-binary"], b"2.0\n")

        control_text = control["./control"][1].decode("utf-8")
        self.assertIn("Package: autosubsync\n", control_text)
        self.assertIn("Version: 9.9-1\n", control_text)
        self.assertIn("Architecture: amd64\n", control_text)
        self.assertIn("Depends: libc6", control_text)
        self.assertIn("Recommends: fonts-dejavu-core, xdg-utils\n", control_text)
        self.assertIn(
            "Description: automatic subtitle synchronization tool\n",
            control_text,
        )

    def test_data_tree_contains_launcher_assets(self):
        """The data archive installs the bundle, symlink, desktop and icon."""
        _, _, data = self._build()

        executable = data["./opt/autosubsync/AutoSubSync"][0]
        self.assertTrue(executable.mode & 0o111)

        launcher = data["./usr/bin/autosubsync"][0]
        self.assertTrue(launcher.issym())
        self.assertEqual(
            launcher.linkname, "../../opt/autosubsync/AutoSubSync"
        )

        desktop = data["./usr/share/applications/autosubsyncapp.desktop"][1]
        self.assertIn(b"Exec=/usr/bin/autosubsync %f", desktop)

        icon_path = (
            "./usr/share/icons/hicolor/256x256/apps/autosubsync.png"
        )
        self.assertIn(icon_path, data)
        self.assertIn("./usr/share/doc/autosubsync/copyright", data)

        changelog = data[
            "./usr/share/doc/autosubsync/changelog.Debian.gz"
        ][1]
        self.assertIn(
            b"autosubsync (9.9-1) unstable; urgency=medium",
            gzip.decompress(changelog),
        )

    def test_checksums_and_maintainer_scripts(self):
        """Control metadata includes checksums and executable maintainer scripts."""
        _, control, _ = self._build()

        md5sums = control["./md5sums"][1].decode("utf-8")
        self.assertIn("  opt/autosubsync/AutoSubSync\n", md5sums)
        self.assertIn("  usr/share/applications/autosubsyncapp.desktop\n", md5sums)
        self.assertNotIn("usr/bin/autosubsync\n", md5sums)

        for script_name in ("./postinst", "./postrm"):
            script = control[script_name][0]
            self.assertTrue(script.mode & 0o111)
            self.assertTrue(control[script_name][1].startswith(b"#!/bin/sh\n"))

    def test_missing_bundle_is_reported(self):
        """A missing PyInstaller bundle raises a clear error."""
        missing_root = os.path.join(self._temp_dir.name, "missing")
        with self.assertRaises(FileNotFoundError):
            linux_packaging.build_deb(missing_root, "9.9", "amd64")


if __name__ == "__main__":
    unittest.main()
