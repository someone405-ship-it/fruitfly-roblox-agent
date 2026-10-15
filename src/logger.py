"""Thread-safe action / status log with ring buffer."""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Deque, List, Tuple

from .config import LOG_LINES


class ActionLogger:
    def __init__(self, maxlen: int = LOG_LINES) -> None:
        self._buf: Deque[Tuple[float, str]] = deque(maxlen=maxlen)
        self._lock = Lock()

    def log(self, msg: str) -> None:
        ts = time.time()
        with self._lock:
            self._buf.append((ts, msg))

    def snapshot(self) -> List[str]:
        with self._lock:
            lines = []
            for ts, msg in self._buf:
                tstr = time.strftime("%H:%M:%S", time.localtime(ts))
                lines.append(f"[{tstr}] {msg}")
            return lines

    def clear(self) -> None:
        with self._lock:
            self._buf.clear()
