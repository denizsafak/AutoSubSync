"""
Qt compatibility layer for PyQt6/PySide6
This module provides a unified interface for both PyQt6 and PySide6
"""

import sys

# Try to import PyQt6 first, fallback to PySide6
try:
    # PyQt6 imports
    from PyQt6.QtWidgets import *
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *

    QT_LIB = "PyQt6"
    print("Qt compatibility: Using PyQt6")

    # PyQt6 uses exec() instead of exec_()
    def exec_():
        """Compatibility wrapper for exec()"""
        return QApplication.exec()

except ImportError:
    try:
        # PySide6 imports
        from PySide6.QtWidgets import *
        from PySide6.QtCore import *
        from PySide6.QtGui import *

        QT_LIB = "PySide6"
        print("Qt compatibility: Using PySide6")

        # PySide6 uses exec() method name
        def exec_():
            """Compatibility wrapper for exec()"""
            return QApplication.exec()

    except ImportError:
        print("ERROR: Neither PyQt6 nor PySide6 is available!")
        sys.exit(1)

# Export the library name for reference
__all__ = ["QT_LIB", "exec_"] + [name for name in dir() if not name.startswith("_")]
