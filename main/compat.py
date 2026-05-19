import sys
import types
import warnings
from pathlib import Path

"""
Compatibility layer for AutoSubSync.
Handles shims for deprecated or removed features in newer Python versions.
"""

# Shim for pkg_resources (removed in Python 3.14+)
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated as an API.*")
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        import pkg_resources
except ImportError:
    # Create a dummy pkg_resources module to satisfy legacy dependencies
    pkg_resources_shim = types.ModuleType("pkg_resources")

    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:
        from importlib_metadata import PackageNotFoundError, version  # type: ignore

    class DistributionNotFound(Exception):
        pass

    class _Distribution:
        def __init__(self, name, dist_version):
            self.project_name = name
            self.version = dist_version

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

    def get_distribution(name):
        try:
            return _Distribution(name, version(name))
        except PackageNotFoundError as e:
            raise DistributionNotFound(name) from e

    def require(name):
        return [get_distribution(name)]

    pkg_resources_shim.resource_filename = resource_filename
    pkg_resources_shim.get_distribution = get_distribution
    pkg_resources_shim.require = require
    pkg_resources_shim.DistributionNotFound = DistributionNotFound
    sys.modules["pkg_resources"] = pkg_resources_shim
