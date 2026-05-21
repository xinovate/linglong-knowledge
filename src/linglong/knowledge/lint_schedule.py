"""Lint schedule daemon — cron-based periodic lint runner."""

import logging
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import schedule

from linglong.core.config import get_config
from linglong.knowledge.lint import LintEngine, LintSeverity
from linglong.knowledge.store import KnowledgeStore

logger = logging.getLogger(__name__)


class CronParseError(ValueError):
    """Raised when a cron expression cannot be parsed."""

    pass


def parse_cron_to_schedule(cron_expr: str) -> schedule.Job:
    """Parse a simplified cron expression into a schedule job.

    Supports format: ``分 时 * * *`` (daily fixed time only).

    Examples:
        ``"0 2 * * *"`` → ``schedule.every().day.at("02:00")``
    """
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise CronParseError(f"cron 表达式必须有 5 个字段，当前 {len(parts)} 个: {cron_expr!r}")

    minute, hour, dom, month, dow = parts

    if dom != "*" or month != "*" or dow != "*":
        raise CronParseError(
            f"当前仅支持 '分 时 * * *' 格式（每天固定时间）: {cron_expr!r}"
        )

    try:
        minute_int = int(minute)
        hour_int = int(hour)
    except ValueError as exc:
        raise CronParseError(f"分/时必须为整数: {cron_expr!r}") from exc

    if not (0 <= minute_int <= 59):
        raise CronParseError(f"分钟必须在 0-59 之间: {minute}")
    if not (0 <= hour_int <= 23):
        raise CronParseError(f"小时必须在 0-23 之间: {hour}")

    time_str = f"{hour_int:02d}:{minute_int:02d}"
    return schedule.every().day.at(time_str)


def _format_lint_log(results: list, start_time: datetime, end_time: datetime) -> str:
    """Format lint results into a single log line summary."""
    counts = {"error": 0, "warning": 0, "info": 0}
    for r in results:
        counts[r.severity.value] = counts.get(r.severity.value, 0) + 1

    start_fmt = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_fmt = end_time.strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"[{start_fmt}] 巡检开始",
        f"[{end_fmt}] 发现问题 {len(results)} 个（error: {counts['error']}, warning: {counts['warning']}, info: {counts['info']}）",
        f"[{end_fmt}] 巡检完成",
    ]
    return "\n".join(lines) + "\n"


def run_lint_and_log(log_path: Path | None = None, stale_days: int = 90) -> int:
    """Run lint once and append results to the schedule log file.

    Returns the exit code (0 = no errors, 1 = has errors).
    """
    if log_path is None:
        log_path = Path.home() / ".linglong" / "logs" / "lint-schedule.log"

    log_path.parent.mkdir(parents=True, exist_ok=True)

    store = KnowledgeStore()
    engine = LintEngine(store)

    start_time = datetime.now(UTC)
    results = engine.run_all(stale_days)
    end_time = datetime.now(UTC)

    log_text = _format_lint_log(results, start_time, end_time)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(log_text)

    has_errors = any(r.severity == LintSeverity.ERROR for r in results)
    return 1 if has_errors else 0


def run_daemon(stale_days: int = 90) -> None:
    """Run lint daemon with graceful shutdown on SIGTERM."""
    config = get_config()
    cron_expr = config.knowledge.lint_schedule

    if not cron_expr:
        logger.error("未配置 lint_schedule，请在 .linglong.yaml 中设置 knowledge.lint_schedule")
        sys.exit(1)

    try:
        job = parse_cron_to_schedule(cron_expr)
    except CronParseError as exc:
        logger.error("cron 解析失败: %s", exc)
        sys.exit(1)

    # Register the job
    job.do(lambda: run_lint_and_log(stale_days=stale_days))

    log_path = Path.home() / ".linglong" / "logs" / "lint-schedule.log"
    logger.info("lint daemon 启动，schedule=%s，日志=%s", cron_expr, log_path)

    # Run once immediately
    logger.info("执行首次巡检...")
    run_lint_and_log(log_path=log_path, stale_days=stale_days)

    # Graceful shutdown handler
    shutdown_requested = False

    def _on_signal(signum, frame):
        nonlocal shutdown_requested
        logger.info("收到信号 %s，准备退出...", signum)
        shutdown_requested = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    while not shutdown_requested:
        schedule.run_pending()
        time.sleep(1)

    logger.info("lint daemon 已退出")
