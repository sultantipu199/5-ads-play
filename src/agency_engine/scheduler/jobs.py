"""Scheduled background jobs with distributed locking."""

from __future__ import annotations

import os
import time
from pathlib import Path

import structlog

logger = structlog.get_logger()


class FileJobLock:
    """Simple robust file lock to prevent concurrent runs across processes."""

    def __init__(self, lock_name: str, lock_dir: Path | None = None, timeout_seconds: int = 600) -> None:
        self.lock_name = lock_name
        self.lock_dir = lock_dir or Path(os.getenv("TEMP", "/tmp")) / "agency_engine_locks"
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file = self.lock_dir / f"{lock_name}.lock"
        self.timeout_seconds = timeout_seconds
        self._acquired = False

    def acquire(self) -> bool:
        now = time.time()
        if self.lock_file.exists():
            try:
                mtime = self.lock_file.stat().st_mtime
                if now - mtime < self.timeout_seconds:
                    logger.warning("job_lock_already_held", lock_name=self.lock_name)
                    return False
                # Lock is expired, safe to reclaim
                self.lock_file.unlink(missing_ok=True)
            except OSError:
                return False

        try:
            with open(self.lock_file, "w", encoding="utf-8") as f:
                f.write(f"pid={os.getpid()};timestamp={now}")
            self._acquired = True
            return True
        except OSError:
            return False

    def release(self) -> None:
        if self._acquired:
            self.lock_file.unlink(missing_ok=True)
            self._acquired = False
