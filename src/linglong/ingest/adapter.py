"""Source adapter interface and registry."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from linglong.core.models import Entity


class SourceAdapter(ABC):
    """Abstract base class for all ingest source adapters."""

    adapter_type: ClassVar[str] = ""

    def __init__(self, source_id: str, config: dict[str, Any], metadata: dict[str, Any]):
        self.source_id = source_id
        self.config = config
        self.metadata = metadata

    @abstractmethod
    async def fetch(self) -> list[Entity]:
        """Fetch data from the source and return a list of Entity objects."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the source is reachable/configured correctly."""
        pass


class AdapterRegistry:
    """Registry for source adapter plugins."""

    _adapters: dict[str, type[SourceAdapter]] = {}

    @classmethod
    def register(cls, adapter_class: type[SourceAdapter]) -> None:
        adapter_type = adapter_class.adapter_type
        if not adapter_type:
            raise ValueError(f"{adapter_class.__name__} must define adapter_type")
        cls._adapters[adapter_type] = adapter_class

    @classmethod
    def get(cls, adapter_type: str) -> type[SourceAdapter] | None:
        return cls._adapters.get(adapter_type)

    @classmethod
    def list_types(cls) -> list[str]:
        return list(cls._adapters.keys())
