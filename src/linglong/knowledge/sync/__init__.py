"""Knowledge sync adapters for external sources."""

from linglong.knowledge.sync.claude_code import ClaudeCodeSyncAdapter
from linglong.knowledge.sync.openclaw import OpenClawSyncAdapter

__all__ = ["ClaudeCodeSyncAdapter", "OpenClawSyncAdapter"]
