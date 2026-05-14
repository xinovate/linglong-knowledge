"""End-to-end integration test: ingest → knowledge → composer → dispatch."""

import uuid
from datetime import datetime
from pathlib import Path

import pytest

from linglong.composer.composer import Composer
from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import Entity, EntityFacet, EntityStatus, Source, SourceType
from linglong.knowledge.store import KnowledgeStore


@pytest.fixture
def pipeline_setup(tmp_path):
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
        facet=EntityFacet.CONCEPT,
        created_by="agent:test",
        confidence=0.92,
        status=EntityStatus.AUTO_CONFIRMED,
        sources=[Source(type=SourceType.RSS, name="test-rss")],
        created_at=date,
    )


def test_full_pipeline_ingest_to_dispatch(pipeline_setup):
    """Full pipeline: simulate ingest → store → composer → dispatch → file."""
    store = KnowledgeStore()
    # 模拟采集步骤：直接在 store 中创建实体
    store.create(
        _create_entity("AI news today: new model released", datetime(2026, 5, 11, 10, 0))
    )
    store.create(
        _create_entity("Tech update: open source tooling improves", datetime(2026, 5, 11, 11, 0))
    )

    # Composer 步骤
    composer = Composer()
    result = composer.run()

    assert result.success is True
    assert len(result.articles) == 1
    article = result.articles[0]
    assert article["dispatch_ready"] is True
    assert "publish_result" in article
    assert article["publish_result"].success is True

    # 验证 dispatch 输出文件存在
    output_dir = pipeline_setup["output_dir"]
    files = list(output_dir.iterdir())
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "AI news today" in content or "Tech update" in content
