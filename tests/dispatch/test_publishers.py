"""Tests for dispatch publishers."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from linglong.dispatch.publishers.hexo import HexoPublisher
from linglong.dispatch.publishers.local import LocalPublisher


def test_local_publisher_article():
    """LocalPublisher writes article to output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "name": "local-test",
            "output_dir": tmpdir,
            "overwrite": False,
        }
        publisher = LocalPublisher(config)
        result = publisher.publish(
            "# Hello World\n\nTest content.",
            {"title": "Test Article", "date": "2026-05-12"},
        )

        assert result.success is True
        assert result.error == ""
        assert (Path(tmpdir) / "2026-05-12_Test_Article.md").exists()


def test_local_publisher_health_check():
    """LocalPublisher health check verifies output dir is writable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {"name": "local-test", "output_dir": tmpdir}
        publisher = LocalPublisher(config)
        assert publisher.health_check() is True


def test_hexo_publisher_git_publish_mock():
    """HexoPublisher git workflow mocked."""
    config = {
        "name": "hexo-test",
        "hexo_path": "/tmp/fake-hexo",
        "use_git_workflow": True,
        "git_remote": "origin",
        "git_branch": "main",
    }
    publisher = HexoPublisher(config)

    # Mock hexo_path exists
    with patch("pathlib.Path.exists", return_value=True):
        with patch(
            "subprocess.run",
            return_value=type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})(),
        ):
            result = publisher.publish(
                "# Test", {"title": "Test", "date": "2026-05-12", "slug": "test"}
            )

    assert result.success is True
    assert "Test" in result.message or "test" in result.message
