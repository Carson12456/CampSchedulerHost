"""
Minimal psutil compatibility shim for test environments without psutil.
"""

from __future__ import annotations

import os


class _MemInfo:
    def __init__(self, rss: int):
        self.rss = rss


class Process:
    def __init__(self, pid: int | None = None):
        self.pid = pid or os.getpid()

    def memory_info(self) -> _MemInfo:
        # Conservative placeholder value for test-only assertions.
        return _MemInfo(rss=0)

