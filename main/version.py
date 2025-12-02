import os
import platform
from datetime import datetime

PROGRAM_NAME = "AutoSubSync"
_current_dir = os.path.dirname(os.path.abspath(__file__))

# Read version from VERSION file
with open(os.path.join(_current_dir, "VERSION"), "r", encoding="utf-8") as version_file:
    version = version_file.read().strip()


def parse_version(version_string):
    """Parse version string into a 4-part tuple for Windows version info."""
    parts = [int(x) for x in version_string.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])  # Ensure exactly 4 parts


version_parts = parse_version(version)

# Only create version info on Windows (required for PyInstaller --version-file)
if platform.system() == "Windows":
    from PyInstaller.utils.win32.versioninfo import (
        VSVersionInfo,
        FixedFileInfo,
        StringFileInfo,
        StringTable,
        StringStruct,
        VarFileInfo,
        VarStruct,
    )

    version_info = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=version_parts,
            prodvers=version_parts,
            mask=0x3F,
            flags=0x0,
            OS=0x40004,  # VOS_NT_WINDOWS32
            fileType=0x1,  # VFT_APP
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        "040904B0",  # US English, Unicode
                        [
                            StringStruct("CompanyName", "Deniz Şafak"),
                            StringStruct(
                                "FileDescription",
                                f"{PROGRAM_NAME} - Automatic subtitle synchronization tool",
                            ),
                            StringStruct("FileVersion", version),
                            StringStruct("InternalName", PROGRAM_NAME),
                            StringStruct(
                                "LegalCopyright", f"© {datetime.now().year} Deniz Şafak"
                            ),
                            StringStruct("OriginalFilename", f"{PROGRAM_NAME}.exe"),
                            StringStruct("ProductName", PROGRAM_NAME),
                            StringStruct("ProductVersion", version),
                        ],
                    )
                ]
            ),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )
else:
    # Placeholder for non-Windows platforms
    version_info = None
