"""Template management for Linglong knowledge base."""

import logging
from pathlib import Path
from typing import Any

from linglong.core.config import get_config
from linglong.core.models import EntityFacet

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE_DIR = Path.home() / "linglong" / "templates"


class TemplateManager:
    """Manage knowledge entry templates by facet."""

    def __init__(self, template_dir: Path | None = None) -> None:
        self.template_dir = template_dir or self._resolve_template_dir()

    def _resolve_template_dir(self) -> Path:
        """Resolve template directory from config or default."""
        try:
            config = get_config()
            if hasattr(config.knowledge, "template_dir"):
                return Path(config.knowledge.template_dir)
        except Exception:
            pass
        return DEFAULT_TEMPLATE_DIR

    def list_templates(self) -> dict[str, dict[str, Any]]:
        """List all available templates with metadata."""
        result: dict[str, dict[str, Any]] = {}
        if not self.template_dir.exists():
            return result

        for path in self.template_dir.glob("*.md"):
            facet = path.stem
            content = path.read_text(encoding="utf-8")
            meta = self._parse_frontmatter(content)
            result[facet] = {
                "facet": facet,
                "description": meta.get("description", ""),
                "path": str(path),
            }
        return result

    def get_template(self, facet: str) -> str | None:
        """Get template content for a given facet name."""
        path = self.template_dir / f"{facet}.md"
        if not path.exists():
            # Try matching against EntityFacet values
            try:
                enum_facet = EntityFacet(facet)
                path = self.template_dir / f"{enum_facet.value}.md"
            except ValueError:
                pass

        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def _parse_frontmatter(self, content: str) -> dict[str, Any]:
        """Extract YAML frontmatter from template content."""
        meta: dict[str, Any] = {}
        if content.startswith("---"):
            try:
                end = content.index("---", 3)
                frontmatter = content[3:end].strip()
                import yaml

                meta = yaml.safe_load(frontmatter) or {}
            except Exception:
                pass
        return meta


# Global instance
_manager: TemplateManager | None = None


def get_template_manager() -> TemplateManager:
    """Get or create the global TemplateManager instance."""
    global _manager
    if _manager is None:
        _manager = TemplateManager()
    return _manager
