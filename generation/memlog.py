"""Memory logging for generation runs on Apple Silicon.

On this machine the GPU shares the 16 GB of system RAM, so three numbers matter:

- ``rss``: resident memory of this Python process.
- ``mps_allocated``: memory held by live MPS tensors.
- ``mps_driver``: everything the Metal driver has reserved for this process
  (tensors plus its cache). This is the number that causes an out-of-memory error.

``MemoryLogger`` samples them in a background thread so peaks inside a long
pipeline call are not missed, and records a named checkpoint whenever asked.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

import psutil

MB = 2**20


def snapshot() -> Dict[str, float]:
    """Current memory use in MB. MPS fields are 0 when torch or MPS is missing."""
    vm = psutil.virtual_memory()
    out = {
        "rss_mb": psutil.Process().memory_info().rss / MB,
        "system_available_mb": vm.available / MB,
        "system_total_mb": vm.total / MB,
        "swap_used_mb": psutil.swap_memory().used / MB,
        "mps_allocated_mb": 0.0,
        "mps_driver_mb": 0.0,
    }
    try:
        import torch

        if torch.backends.mps.is_available():
            out["mps_allocated_mb"] = torch.mps.current_allocated_memory() / MB
            out["mps_driver_mb"] = torch.mps.driver_allocated_memory() / MB
    except ImportError:
        pass
    return out


class MemoryLogger:
    """Use as a context manager; call ``mark(label)`` at points of interest."""

    PEAK_KEYS = ("rss_mb", "mps_allocated_mb", "mps_driver_mb", "swap_used_mb")

    def __init__(self, interval: float = 0.25, verbose: bool = True):
        self.interval = interval
        self.verbose = verbose
        self.checkpoints: List[Dict[str, float]] = []
        self.peak: Dict[str, float] = {k: 0.0 for k in self.PEAK_KEYS}
        self.min_system_available_mb = float("inf")
        self._start = time.time()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _update(self, snap: Dict[str, float]) -> None:
        for key in self.PEAK_KEYS:
            self.peak[key] = max(self.peak[key], snap[key])
        self.min_system_available_mb = min(
            self.min_system_available_mb, snap["system_available_mb"]
        )

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            self._update(snapshot())

    def __enter__(self) -> "MemoryLogger":
        self._start = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.mark("start")
        return self

    def __exit__(self, *exc) -> None:
        self.mark("end")
        self._stop.set()
        if self._thread is not None:
            self._thread.join()

    def mark(self, label: str) -> Dict[str, float]:
        snap = snapshot()
        self._update(snap)
        entry = {"label": label, "t_s": round(time.time() - self._start, 2), **snap}
        self.checkpoints.append(entry)
        if self.verbose:
            print(
                f"[mem] {label:<22} t={entry['t_s']:7.1f}s  "
                f"rss={snap['rss_mb']:7.0f} MB  "
                f"mps={snap['mps_allocated_mb']:7.0f} MB  "
                f"driver={snap['mps_driver_mb']:7.0f} MB  "
                f"free={snap['system_available_mb']:7.0f} MB",
                flush=True,
            )
        return entry

    def summary(self) -> Dict[str, object]:
        return {
            "peak": {k: round(v, 1) for k, v in self.peak.items()},
            "min_system_available_mb": round(self.min_system_available_mb, 1),
            "duration_s": round(time.time() - self._start, 2),
            "checkpoints": self.checkpoints,
        }

    def save(self, path: Path, extra: Optional[Dict[str, object]] = None) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {**(extra or {}), "memory": self.summary()}
        path.write_text(json.dumps(payload, indent=2))
        return path
