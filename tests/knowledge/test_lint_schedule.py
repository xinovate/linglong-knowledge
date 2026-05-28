"""Lint schedule daemon tests."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.knowledge.lint_schedule import (
    CronParseError,
    parse_cron_to_schedule,
    run_daemon,
    run_lint_and_log,
)


class TestCronParser:
    """Tests for cron expression parser."""

    def test_cron_parser_basic(self):
        """Verify '0 2 * * *' parses to schedule.every().day.at('02:00')."""
        job = parse_cron_to_schedule("0 2 * * *")
        assert job is not None
        # schedule.Job exposes .at_time when configured with .at()
        assert job.at_time is not None
        assert job.at_time.hour == 2
        assert job.at_time.minute == 0

    def test_cron_parser_different_time(self):
        """Verify other valid daily times parse correctly."""
        job = parse_cron_to_schedule("30 14 * * *")
        assert job.at_time.hour == 14
        assert job.at_time.minute == 30

    def test_cron_parser_invalid_format(self):
        """Verify invalid cron expressions raise CronParseError."""
        with pytest.raises(CronParseError, match="必须有 5 个字段"):
            parse_cron_to_schedule("0 2 * *")

        with pytest.raises(CronParseError, match="仅支持"):
            parse_cron_to_schedule("0 2 1 * *")

        with pytest.raises(CronParseError, match="分/时必须为整数"):
            parse_cron_to_schedule("abc 2 * * *")

        with pytest.raises(CronParseError, match="分钟必须在 0-59"):
            parse_cron_to_schedule("60 2 * * *")

        with pytest.raises(CronParseError, match="小时必须在 0-23"):
            parse_cron_to_schedule("0 24 * * *")


class TestDaemonMode:
    """Tests for daemon mode behaviour."""

    @pytest.fixture
    def mock_config(self):
        """Provide a config with lint_schedule set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LinglongConfig(
                knowledge=LinglongConfig().knowledge.model_copy(update={
                    "wiki_path": Path(tmpdir) / "wiki",
                    "db_path": Path(tmpdir) / "knowledge.db",
                    "generate_embeddings": False,
                    "lint_schedule": "0 2 * * *",
                }),
            )
            set_config(config)
            yield config

    def test_run_scheduled_once(self, mock_config, tmp_path):
        """Verify run_lint_and_log executes once and writes to log."""
        log_path = tmp_path / "lint-schedule.log"
        exit_code = run_lint_and_log(log_path=log_path, stale_days=90)

        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        assert "巡检开始" in content
        assert "巡检完成" in content
        # Empty KB has no issues
        assert exit_code == 0

    def test_daemon_mode_runs_once(self, mock_config):
        """Mock schedule to verify daemon runs at least one lint cycle."""
        with patch("linglong.knowledge.lint_schedule.schedule") as mock_schedule:
            mock_job = MagicMock()
            mock_schedule.every.return_value.day.at.return_value = mock_job

            with patch("linglong.knowledge.lint_schedule.run_lint_and_log") as mock_run:
                with patch("linglong.knowledge.lint_schedule.signal") as mock_signal:
                    with patch("linglong.knowledge.lint_schedule.time") as mock_time:
                        # First sleep raises KeyboardInterrupt to break loop
                        mock_time.sleep.side_effect = [None, KeyboardInterrupt]
                        with pytest.raises(KeyboardInterrupt):
                            run_daemon(stale_days=90)

            # Verify schedule was configured
            mock_schedule.every.assert_called_once()
            mock_job.do.assert_called_once()
            # Verify immediate run happened
            mock_run.assert_called_once()

    def test_daemon_exits_without_schedule(self):
        """Daemon exits with error when lint_schedule is not configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LinglongConfig(
                knowledge=LinglongConfig().knowledge.model_copy(update={
                    "wiki_path": Path(tmpdir) / "wiki",
                    "db_path": Path(tmpdir) / "knowledge.db",
                    "generate_embeddings": False,
                    "lint_schedule": None,
                }),
            )
            set_config(config)

            with pytest.raises(SystemExit) as exc_info:
                run_daemon()
            assert exc_info.value.code == 1

    def test_daemon_exits_on_bad_cron(self):
        """Daemon exits with error when cron expression is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LinglongConfig(
                knowledge=LinglongConfig().knowledge.model_copy(update={
                    "wiki_path": Path(tmpdir) / "wiki",
                    "db_path": Path(tmpdir) / "knowledge.db",
                    "generate_embeddings": False,
                    "lint_schedule": "invalid",
                }),
            )
            set_config(config)

            with pytest.raises(SystemExit) as exc_info:
                run_daemon()
            assert exc_info.value.code == 1
