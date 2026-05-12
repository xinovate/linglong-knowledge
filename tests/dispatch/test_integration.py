"""Integration test: composer DraftManager → DispatchManager."""

import pytest

from linglong.composer.draft import DraftManager
from linglong.core.config import LinglongConfig, set_config
from linglong.dispatch.manager import DispatchManager


@pytest.fixture
def integrated_setup(tmp_path):
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = LinglongConfig(
        data_dir=tmp_path / "data",
        composer=LinglongConfig().composer.model_copy(update={"drafts_dir": drafts_dir}),
        knowledge=LinglongConfig().knowledge.model_copy(
            update={
                "wiki_path": tmp_path / "wiki",
                "db_path": tmp_path / "knowledge.db",
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
    return {"drafts_dir": drafts_dir, "output_dir": output_dir}


def test_draft_to_publish_pipeline(integrated_setup):
    """Full pipeline: create draft → publish draft → dispatch publishes file."""
    dm = DraftManager()
    entry = dm.save_draft(
        title="Integration Test",
        date="2026-05-12",
        content="---\ntitle: Integration Test\ndate: 2026-05-12\n---\n\n# Hello",
        metadata={"title": "Integration Test"},
        fragment_hashes=["abc123"],
    )

    payload = dm.publish_draft(entry.id)
    assert payload["status"] == "dispatch_ready"

    dispatch = DispatchManager()
    result = dispatch.publish(payload)
    assert result.success is True
    assert (integrated_setup["output_dir"] / "2026-05-12_Integration_Test.md").exists()
