import os
import platform
from datetime import datetime
from texts import PROGRAM_NAME

# Only import Windows-specific modules on Windows
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

with open(os.path.join(os.path.dirname(__file__), "VERSION"), "r") as version_file:
    version = version_file.read().strip()


def parse_version():
    parts = [int(x) for x in version.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts)


version_parts = parse_version()

# Only create VSVersionInfo on Windows
if platform.system() == "Windows":
    VSVersionInfo = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=version_parts,
            prodvers=version_parts,
            mask=0x3F,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        "040904B0",
                        [
                            StringStruct("CompanyName", "Deniz Şafak"),
                            StringStruct(
                                "FileDescription",
                                f"{PROGRAM_NAME} is a user-friendly Python tool that helps you easily synchronize subtitle files.",
                            ),
                            StringStruct("FileVersion", version),
                            StringStruct("InternalName", PROGRAM_NAME),
                            StringStruct(
                                "LegalCopyright", f"(c) {datetime.now().year}"
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
    # Dummy VSVersionInfo for non-Windows platforms
    VSVersionInfo = None
