"""Tests for Linglong CLI."""

import pytest

from linglong.cli import main


def test_cli_help():
    """CLI should show help without error."""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_cli_ingest_no_packages(tmp_path, monkeypatch):
    """ingest with no packages should warn and exit 1."""
    from linglong.core.config import LinglongConfig, set_config

    config = LinglongConfig(
        data_dir=tmp_path / "data",
        ingest=LinglongConfig().ingest.model_copy(
            update={"package_paths": [str(tmp_path / "nonexistent")]}
        ),
    )
    set_config(config)

    code = main(["ingest"])
    assert code == 1


def test_cli_compose_dry_run(tmp_path, monkeypatch):
    """compose --dry-run should succeed with empty store."""
    from linglong.core.config import LinglongConfig, set_config

    config = LinglongConfig(
        data_dir=tmp_path / "data",
        knowledge=LinglongConfig().knowledge.model_copy(
            update={
                "wiki_path": tmp_path / "wiki",
                "db_path": tmp_path / "knowledge.db",
            }
        ),
        composer=LinglongConfig().composer.model_copy(
            update={"drafts_dir": tmp_path / "drafts"}
        ),
    )
    set_config(config)

    code = main(["compose", "--dry-run"])
    assert code == 0
