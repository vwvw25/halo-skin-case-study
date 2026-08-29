"""Import shim for WeasyPrint.

On macOS with Homebrew, WeasyPrint can only find libpango/libcairo if
``DYLD_FALLBACK_LIBRARY_PATH`` points at the Homebrew lib dir. dyld reads that variable per
``dlopen``, so setting it here (before the first ``import weasyprint``) is enough. On Linux the
loader finds the system libs and this is a no-op.
"""

from __future__ import annotations

import os
import sys

if sys.platform == "darwin":
    _existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    _brew_libs = ["/opt/homebrew/lib", "/usr/local/lib"]
    _merged = os.pathsep.join(p for p in [_existing, *_brew_libs] if p)
    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = _merged

from weasyprint import HTML

__all__ = ["HTML"]
