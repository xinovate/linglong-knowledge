"""Tests for adapter interface and registry."""

import pytest

from linglong.core.models import Entity
from linglong.ingest.adapter import AdapterRegistry, SourceAdapter


class MockAdapter(SourceAdapter):
    adapter_type = "mock"

    async def fetch(self) -> list[Entity]:
        return []

    def health_check(self) -> bool:
        return True


def test_adapter_registry_register_and_get():
    """AdapterRegistry can register and retrieve adapters."""
    AdapterRegistry.register(MockAdapter)
    assert AdapterRegistry.get("mock") is MockAdapter
    assert "mock" in AdapterRegistry.list_types()


def test_adapter_registry_unknown_type():
    """Unknown adapter type returns None."""
    assert AdapterRegistry.get("nonexistent") is None


def test_adapter_missing_type_raises():
    """Adapter without adapter_type raises ValueError."""

    class BadAdapter(SourceAdapter):
        pass

    with pytest.raises(ValueError):
        AdapterRegistry.register(BadAdapter)
