"""Tests for dispatch publishers."""

import tempfile
from pathlib import Path

import pytest

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
