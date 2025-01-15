"""pyinstaller hook file.

You need to use this hook-file if you are packaging a project using tkinterdnd2.
Just put hook-tkinterdnd2.py in the same directory where you call pyinstaller and type:

    pyinstaller myproject/myproject.py --additional-hooks-dir=.
"""

from PyInstaller.utils.hooks import collect_data_files, eval_statement


datas = collect_data_files('tkinterdnd2')
