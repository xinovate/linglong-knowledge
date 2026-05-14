"""文件锁机制测试。"""

import tempfile
from pathlib import Path

import pytest

from linglong.knowledge.lock import KnowledgeLock, LockError


@pytest.fixture
def lock_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_lock_acquire_release(lock_dir):
    """锁可以正常获取和释放。"""
    lock = KnowledgeLock(lock_dir / "test.lock", timeout=1.0)
    lock.acquire()
    assert lock._fd is not None
    lock.release()
    assert lock._fd is None


def test_lock_context_manager(lock_dir):
    """锁支持上下文管理器。"""
    lock_path = lock_dir / "ctx.lock"
    with KnowledgeLock(lock_path, timeout=1.0):
        assert lock_path.exists()


def test_lock_timeout(lock_dir):
    """锁超时时抛出 LockError。"""
    lock_path = lock_dir / "timeout.lock"
    # 先占用锁
    holder = KnowledgeLock(lock_path, timeout=0.5)
    holder.acquire()

    # 第二个锁应该超时
    contender = KnowledgeLock(lock_path, timeout=0.5)
    with pytest.raises(LockError):
        contender.acquire()

    holder.release()


def test_lock_reentrant_after_release(lock_dir):
    """释放后可以重新获取。"""
    lock_path = lock_dir / "reentrant.lock"
    lock = KnowledgeLock(lock_path, timeout=1.0)
    lock.acquire()
    lock.release()
    lock.acquire()  # 应该成功
    lock.release()
