"""API source adapter — REST API calls."""

import httpx

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityFacet, Source, SourceType
from linglong.ingest.adapter import SourceAdapter


class APIAdapter(SourceAdapter):
    """Adapter for REST API endpoints."""

    adapter_type = "api"

    async def fetch(self) -> list[Entity]:
        endpoint = self.config["endpoint"]
        method = self.config.get("method", "GET")
        headers = self.config.get("headers", {})
        params = self._resolve_params(self.config.get("params", {}))
        default_timeout = get_config().ingest.api_timeout
        timeout = self.config.get("timeout", default_timeout)

        async with httpx.AsyncClient(timeout=timeout) as client:
            if method.upper() == "GET":
                response = await client.get(endpoint, headers=headers, params=params)
            else:
                response = await client.request(method, endpoint, headers=headers, json=params)
            response.raise_for_status()
            data = response.json()

        return self._parse_response(data)

    def _resolve_params(self, params: dict) -> dict:
        from datetime import datetime, timedelta

        resolved = {}
        for key, value in params.items():
            if isinstance(value, str):
                if "{date-7d}" in value:
                    date_str = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                    value = value.replace("{date-7d}", date_str)
                elif "{date-3d}" in value:
                    date_str = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
                    value = value.replace("{date-3d}", date_str)
            resolved[key] = value
        return resolved

    def _parse_response(self, data: dict | list) -> list[Entity]:
        items = data if isinstance(data, list) else data.get("items", []) or data.get("results", [])
        return [self._item_to_entity(item) for item in items]

    def _item_to_entity(self, item: dict) -> Entity:
        return Entity(
            content=f"```json\n{item}\n```",
            facet=EntityFacet.REFERENCE,
            created_by="agent:ingest",
            confidence=get_config().ingest.default_confidence.get("api", 0.75),
            sources=[
                Source(
                    type=SourceType.API,
                    name=self.source_id,
                    metadata={"authority": self.metadata.get("authority", "high")},
                )
            ],
        )

    def health_check(self) -> bool:
        return bool(self.config.get("endpoint"))
