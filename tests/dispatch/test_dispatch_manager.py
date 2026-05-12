"""Tests for DispatchManager."""

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.dispatch.manager import DispatchManager


@pytest.fixture(autouse=True)
def _reset_config(tmp_path):
    config = LinglongConfig(
        data_dir=tmp_path / "data",
        knowledge=LinglongConfig().knowledge.model_copy(
            update={
                "wiki_path": tmp_path / "wiki",
                "db_path": tmp_path / "knowledge.db",
            }
        ),
        dispatch=LinglongConfig().dispatch.model_copy(
            update={
                "enabled": True,
                "default_publisher": "local",
                "publishers": [
                    {
                        "name": "local",
                        "type": "local",
                        "enabled": True,
                        "config": {
                            "output_dir": str(tmp_path / "output"),
                            "overwrite": True,
                        },
                    }
                ],
            }
        ),
    )
    set_config(config)


def test_dispatch_manager_list_publishers():
    """DispatchManager initializes enabled publishers from config."""
    manager = DispatchManager()
    assert manager.list_publishers() == ["local"]


def test_dispatch_manager_publish_routing():
    """DispatchManager routes payload to configured publisher."""
    manager = DispatchManager()
    payload = {
        "draft_id": "test-123",
        "content": "# Hello",
        "metadata": {"title": "Hello", "date": "2026-05-12"},
    }
    result = manager.publish(payload)
    assert result.success is True
    assert "已保存到" in result.message


def test_dispatch_manager_publish_unknown_publisher():
    """Publishing to unknown publisher returns error result."""
    manager = DispatchManager()
    result = manager.publish({}, publisher_name="nonexistent")
    assert result.success is False
    assert "not found" in result.error
