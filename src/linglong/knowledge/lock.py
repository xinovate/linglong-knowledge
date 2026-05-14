"""基于文件的互斥锁，用于 knowledge store 写操作。"""

import fcntl
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class LockError(Exception):
    """获取锁失败时抛出。"""
    pass


class KnowledgeLock:
    """基于 fcntl.flock 的跨进程文件锁。

    支持 Unix 系统上的互斥写入，可配置超时时间。
    """

    def __init__(self, lock_path: Path, timeout: float = 5.0):
        self.lock_path = lock_path
        self.timeout = timeout
        self._fd = None

    def acquire(self) -> None:
        """获取锁，最多等待 timeout 秒。"""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = open(self.lock_path, "w")

        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._fd.write(f"{time.monotonic()}\n")
                self._fd.flush()
                return
            except (IOError, OSError):
                if time.monotonic() >= deadline:
                    self._fd.close()
                    self._fd = None
                    raise LockError(
                        f"无法在 {self.timeout}s 内获取锁：{self.lock_path}"
                    )
                time.sleep(0.1)

    def release(self) -> None:
        """释放锁。"""
        if self._fd:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                self._fd.close()
            except (IOError, OSError):
                pass
            finally:
                self._fd = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False
