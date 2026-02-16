"""
Centralized ExifTool path resolution for both development and frozen (PyInstaller) environments.

When running as a frozen app, returns the path to the bundled exiftool script
and configures PERL5LIB. Otherwise returns 'exiftool' for system PATH lookup.
"""

import sys
import os
from pathlib import Path


def get_exiftool_path() -> str:
    """
    Get the path to the exiftool executable.

    Returns:
        Path to exiftool (absolute path when frozen, 'exiftool' otherwise)
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        bundle_dir = Path(sys._MEIPASS)
        exiftool_path = bundle_dir / 'exiftool_perl' / 'exiftool'

        # Set PERL5LIB so the bundled Perl modules are found
        lib_path = str(bundle_dir / 'exiftool_perl' / 'lib')
        os.environ['PERL5LIB'] = lib_path

        return str(exiftool_path)
    else:
        # Development: use system exiftool from PATH
        return 'exiftool'


def get_exiftool_helper(**kwargs):
    """
    Create an ExifToolHelper instance with the correct exiftool path.

    Args:
        **kwargs: Additional keyword arguments passed to ExifToolHelper

    Returns:
        exiftool.ExifToolHelper instance
    """
    import exiftool

    executable = get_exiftool_path()
    if getattr(sys, 'frozen', False):
        return exiftool.ExifToolHelper(executable=executable, **kwargs)
    else:
        return exiftool.ExifToolHelper(**kwargs)
