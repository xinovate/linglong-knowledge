"""Integration test: Composer.run() with auto_publish dispatches to publisher."""

import uuid
from datetime import datetime
from pathlib import Path

import pytest

from linglong.composer.composer import Composer
from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import Entity, EntityStatus, Source, SourceType
from linglong.knowledge.store import KnowledgeStore


@pytest.fixture
def auto_publish_setup(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = LinglongConfig(
        data_dir=tmp_path / "data",
        knowledge=LinglongConfig().knowledge.model_copy(
            update={
                "wiki_path": tmp_path / "wiki",
                "db_path": tmp_path / "knowledge.db",
            }
        ),
        composer=LinglongConfig().composer.model_copy(
            update={
                "drafts_dir": tmp_path / "drafts",
                "auto_publish": True,
                "default_publisher": "local",
            }
        ),
        dispatch=LinglongConfig().dispatch.model_copy(
            update={
                "default_publisher": "local",
                "publishers": [
                    {
                        "name": "local",
                        "type": "local",
                        "enabled": True,
                        "config": {
                            "output_dir": str(output_dir),
                            "overwrite": True,
                        },
                    }
                ],
            }
        ),
    )
    set_config(config)

    # 清除全局 composer 状态，避免测试间污染
    from linglong.composer.state import _default_state_file

    state_file = _default_state_file()
    if state_file.exists():
        state_file.unlink()

    return {"output_dir": output_dir}


def _create_entity(content: str, date: datetime) -> Entity:
    return Entity(
        id=str(uuid.uuid4()),
        content=content,
        created_by="agent:test",
        confidence=0.92,
        status=EntityStatus.AUTO_CONFIRMED,
        sources=[Source(type=SourceType.MEMORY, name="test")],
        created_at=date,
    )


def test_composer_auto_publish(auto_publish_setup):
    """Composer with auto_publish=True should output file via LocalPublisher."""
    store = KnowledgeStore()
    store.create(_create_entity("测试内容", datetime(2026, 5, 11, 10, 0)))

    composer = Composer()
    result = composer.run()

    assert result.success is True
    assert len(result.articles) == 1
    article = result.articles[0]
    assert article["dispatch_ready"] is True

    # 验证 publish_result 存在
    assert "publish_result" in article
    assert article["publish_result"].success is True

    # 验证文件由 LocalPublisher 写入
    output_dir = auto_publish_setup["output_dir"]
    files = list(output_dir.iterdir())
    assert len(files) == 1
    assert "2026-05-11" in files[0].name


def test_composer_auto_publish_off(auto_publish_setup):
    """Composer with auto_publish=False should not publish."""
    from linglong.core.config import get_config

    config = get_config()
    config.composer.auto_publish = False

    store = KnowledgeStore()
    store.create(_create_entity("测试内容", datetime(2026, 5, 11, 10, 0)))

    composer = Composer()
    result = composer.run()

    assert result.success is True
    assert len(result.articles) == 1
    article = result.articles[0]
    assert "publish_result" not in article

    output_dir = auto_publish_setup["output_dir"]
    files = list(output_dir.iterdir())
    assert len(files) == 0
