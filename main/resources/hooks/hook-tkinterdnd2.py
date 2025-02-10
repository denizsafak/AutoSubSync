"""pyinstaller hook file.

You need to use this hook-file if you are packaging a project using tkinterdnd2.
Just put hook-tkinterdnd2.py in the same directory where you call pyinstaller and type:

    pyinstaller myproject/myproject.py --additional-hooks-dir=.
"""

from PyInstaller.utils.hooks import collect_data_files, get_package_paths
import os
import glob

# Collect data files from the tkinterdnd2 package
datas = collect_data_files("tkinterdnd2")

# Dynamically find and add the shared library for Linux (both x64 and arm64)
package_path = get_package_paths("tkinterdnd2")[1]
libtkdnd_patterns = [
    os.path.join(package_path, "tkdnd", "linux-x64", "libtkdnd*.so"),
    os.path.join(package_path, "tkdnd", "linux-arm64", "libtkdnd*.so"),
]

for pattern in libtkdnd_patterns:
    libtkdnd_files = glob.glob(pattern)
    if libtkdnd_files:
        for libtkdnd_file in libtkdnd_files:
            datas.append(
                (
                    libtkdnd_file,
                    os.path.join(
                        "tkinterdnd2",
                        "tkdnd",
                        os.path.basename(os.path.dirname(pattern)),
                    ),
                )
            )
    else:
        print(f"Warning: No libtkdnd*.so files found in {os.path.dirname(pattern)}")
