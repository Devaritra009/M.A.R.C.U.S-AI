"""
Memory optimization utility for MARCUS.
Provides generational garbage collection and OS working set release.
"""
from __future__ import annotations

import gc
import sys


def optimize_ram() -> None:
    """Run generational garbage collection and release free memory back to the OS."""
    try:
        gc.collect(2)
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
    except Exception:
        pass
