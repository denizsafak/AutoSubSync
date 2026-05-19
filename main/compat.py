import sys
import types
from pathlib import Path

"""
Compatibility layer for AutoSubSync.
Handles shims for deprecated or removed features in newer Python versions.
"""

# Shim for pkg_resources (removed in Python 3.14+)
try:
    import pkg_resources
except ImportError:
    # Create a dummy pkg_resources module to satisfy legacy dependencies
    pkg_resources_shim = types.ModuleType("pkg_resources")

    def resource_filename(package_or_requirement, resource_name):
        """
        Implementation of resource_filename for legacy libraries (like autosubsync).
        """
        try:
            module = sys.modules.get(package_or_requirement)
            if module and hasattr(module, "__file__") and module.__file__:
                return str(Path(module.__file__).parent / resource_name)
        except Exception:
            pass
        return resource_name

    pkg_resources_shim.resource_filename = resource_filename
    sys.modules["pkg_resources"] = pkg_resources_shim
