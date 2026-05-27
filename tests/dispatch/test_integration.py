"""Integration test: DispatchManager publish flow."""

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.dispatch.manager import DispatchManager


@pytest.fixture
def dispatch_setup(tmp_path):
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
    return {"output_dir": output_dir}


def test_dispatch_publishes_file(dispatch_setup):
    """DispatchManager publishes a markdown file via local publisher."""
    dispatch = DispatchManager()
    content = "---\ntitle: Integration Test\ndate: 2026-05-12\n---\n\n# Hello"
    result = dispatch.publish(
        {"content": content, "metadata": {"title": "Integration Test", "date": "2026-05-12"}},
        publisher_name="local",
    )
    assert result.success is True
    assert (dispatch_setup["output_dir"] / "2026-05-12_Integration_Test.md").exists()
